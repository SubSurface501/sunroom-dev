import logging
import os
import json
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as PDFImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from db import crud

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PublisherAgent:
    """
    The Typesetter.
    Compiles the Storybook Manifest and Images into a printable PDF.
    """
    def __init__(self, db, worker=None, llm=None):
        self.db = db
        self.worker = worker
        self.llm = llm

    def run_task(self, user_id: str, trailhead_id: str):
        logger.info(f"Starting Publisher for Trailhead {trailhead_id}")

        # 1. Fetch Data
        try:
            # Assuming self.db is the Supabase client based on previous patterns
            response = self.db.table("Trailheads").select("*").eq("id", trailhead_id).eq("user_id", user_id).single().execute()
            trailhead = response.data
            if not trailhead: 
                logger.error("Trailhead not found")
                return
        except Exception as e:
            logger.error(f"DB Error: {e}")
            return

        manifest = trailhead.get('content', {})
        pages = manifest.get('pages', [])
        title = manifest.get('project_title', 'Untitled Storybook')

        # 2. Setup Paths
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        # Images are here
        img_dir = os.path.join(root_path, "worker", "output", "images", trailhead_id)
        
        # Sanitize Title for Windows Filename compatibility
        safe_title = title.replace(':', '-').replace('/', '-').replace('\\', '-').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
        safe_title = safe_title.replace(' ', '_')
        
        # PDF saves to here
        pdf_path = os.path.join(img_dir, f"{safe_title}.pdf")

        # Ensure directory exists (it should if images were generated)
        if not os.path.exists(img_dir):
            os.makedirs(img_dir, exist_ok=True)

        # 3. PDF Setup
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(letter),
            rightMargin=36, leftMargin=36,
            topMargin=36, bottomMargin=36
        )

        story = []
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'Title', parent=styles['Heading1'], alignment=1, fontSize=24, spaceAfter=20
        )
        body_style = ParagraphStyle(
            'Body', parent=styles['BodyText'], alignment=0, fontSize=14, leading=18, spaceBefore=10
        )
        caption_style = ParagraphStyle(
            'Caption', parent=styles['Italic'], alignment=1, fontSize=10, textColor=colors.gray
        )

        # 4. Build Content
        # Title Page
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"Narrated by: {manifest.get('narrator_voice_check', 'The System')}", caption_style))
        story.append(Spacer(1, 2 * inch))
        
        # Add Concept Art if available
        assets = manifest.get('asset_references', {})
        if assets:
            story.append(Paragraph("Character & Concept Studies", styles['Heading2']))
            story.append(Spacer(1, 0.2 * inch))
            for name, path in assets.items():
                if os.path.exists(path):
                    try:
                        # Resize to fit
                        img = PDFImage(path, width=4*inch, height=2.25*inch, kind='proportional')
                        story.append(img)
                        story.append(Paragraph(name, caption_style))
                        story.append(Spacer(1, 0.2 * inch))
                    except Exception as e:
                        logger.warning(f"Could not add image {path}: {e}")
            story.append(PageBreak())

        # Story Pages
        for page in pages:
            page_num = page.get('page_number')
            text = page.get('narrative_text', '')
            img_path = page.get('image_url', '') # Note: In your illustrator, you stored local paths here

            # Image
            if img_path and os.path.exists(img_path):
                try:
                    # 16:9 Aspect Ratio usually fits nicely on landscape letter
                    img = PDFImage(img_path, width=8*inch, height=4.5*inch, kind='proportional')
                    story.append(img)
                except Exception as e:
                    story.append(Paragraph(f"[Image Error: {e}]", caption_style))
            else:
                story.append(Paragraph("[Image Missing]", caption_style))

            story.append(Spacer(1, 0.2 * inch))

            # Text
            story.append(Paragraph(text, body_style))
            
            # Page Number
            story.append(Spacer(1, 0.5 * inch))
            story.append(Paragraph(f"- {page_num} -", caption_style))
            
            story.append(PageBreak())

        # 5. Build
        try:
            doc.build(story)
            logger.info(f"PDF Successfully Generated: {pdf_path}")
            
            # Optional: Update DB with PDF path
            # We can update the trailhead content to include the PDF path
            manifest['pdf_path'] = pdf_path
            self.db.table("Trailheads").update({"content": manifest}).eq("id", trailhead_id).execute()
            
        except Exception as e:
            logger.error(f"PDF Generation Failed: {e}")
