import logging
import os
import json
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as PDFImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from db import crud
from storage.client import upload_file

logger = logging.getLogger(__name__)

class PublisherAgent:
    """
    The Typesetter.
    Compiles the Storybook Manifest and Images into a printable PDF and uploads to storage.
    """
    def __init__(self, db, worker=None, llm=None):
        self.db = db
        self.worker = worker
        self.llm = llm

    def run_task(self, user_id: str, node_id: str):
        logger.info(f"Starting Publisher for Node {node_id}")

        # 1. Fetch Data
        try:
            response = self.db.table("Nodes").select("*").eq("id", node_id).single().execute()
            node = response.data
            if not node: 
                logger.error("Node not found")
                return
        except Exception as e:
            logger.error(f"DB Error: {e}")
            return

        manifest = node.get('content', {})
        pages = manifest.get('pages', [])
        title = node.get('title', 'Untitled Storybook')

        # 2. Setup Paths
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        img_dir = os.path.join(root_path, "worker", "output", "images", node_id)
        
        safe_title = title.replace(':', '-').replace('/', '-').replace('\\', '-').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '|').replace('|', '')
        safe_title = safe_title.replace(' ', '_')
        
        pdf_path = os.path.join(img_dir, f"{safe_title}.pdf")

        if not os.path.exists(img_dir):
            os.makedirs(img_dir, exist_ok=True)

        # 3. Upload Images and update manifest
        updated_pages = []
        for page in pages:
            page_num = page.get('page_number')
            local_img_path = page.get('image_url', '')
            
            if local_img_path and os.path.exists(local_img_path):
                try:
                    file_name = os.path.basename(local_img_path)
                    destination_path = f"{node_id}/{file_name}"
                    public_url = upload_file("storybook_images", local_img_path, destination_path)
                    page['image_url'] = public_url
                    logger.info(f"Uploaded image for page {page_num} to {public_url}")
                except Exception as e:
                    logger.error(f"Failed to upload image for page {page_num}: {e}")
            
            updated_pages.append(page)

        manifest['pages'] = updated_pages

        # 4. PDF Setup and Generation
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(letter),
            rightMargin=36, leftMargin=36,
            topMargin=36, bottomMargin=36
        )

        story = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=24, spaceAfter=20)
        body_style = ParagraphStyle('Body', parent=styles['BodyText'], alignment=0, fontSize=14, leading=18, spaceBefore=10)
        caption_style = ParagraphStyle('Caption', parent=styles['Italic'], alignment=1, fontSize=10, textColor=colors.gray)

        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"Narrated by: {manifest.get('narrator_voice_check', 'The System')}", caption_style))
        story.append(Spacer(1, 2 * inch))

        for page in manifest['pages']:
            page_num = page.get('page_number')
            text = page.get('narrative_text', '')
            img_path = page.get('image_url', '')

            if img_path and os.path.exists(img_path):
                try:
                    img = PDFImage(img_path, width=8*inch, height=4.5*inch, kind='proportional')
                    story.append(img)
                except Exception as e:
                    story.append(Paragraph(f"[Image Error: {e}]", caption_style))
            else:
                story.append(Paragraph("[Image Missing]", caption_style))

            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph(text, body_style))
            story.append(Spacer(1, 0.5 * inch))
            story.append(Paragraph(f"- {page_num} -", caption_style))
            story.append(PageBreak())

        try:
            doc.build(story)
            logger.info(f"PDF Successfully Generated: {pdf_path}")
            
            # Upload PDF
            pdf_destination_path = f"{node_id}/{safe_title}.pdf"
            pdf_public_url = upload_file("storybook_pdfs", pdf_path, pdf_destination_path)
            manifest['pdf_path'] = pdf_public_url
            manifest['production_status'] = 'published'
            logger.info(f"Uploaded PDF to {pdf_public_url}")

            # 5. Final DB Update
            self.db.table("Nodes").update({"content": manifest}).eq("id", node_id).execute()
            
        except Exception as e:
            logger.error(f"PDF Generation or Upload Failed: {e}")
