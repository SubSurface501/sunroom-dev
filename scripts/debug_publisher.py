import os
import sys
import logging
import json
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as PDFImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from dotenv import load_dotenv
from supabase import create_client

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
db_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# IDs
USER_ID = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d"
TRAILHEAD_ID = "8131ca68-7373-4ab7-9cdd-ebce0f8106cb"

def debug_pdf_generation():
    print(f"Debugging Publisher for Trailhead {TRAILHEAD_ID}...")

    # 1. Fetch Data
    try:
        response = db_client.table("Trailheads").select("*").eq("id", TRAILHEAD_ID).eq("user_id", USER_ID).single().execute()
        trailhead = response.data
        if not trailhead: 
            print("Error: Trailhead not found")
            return
    except Exception as e:
        print(f"DB Error: {e}")
        return

    manifest = trailhead.get('content', {})
    pages = manifest.get('pages', [])
    title = manifest.get('project_title', 'Untitled Storybook')
    
    print(f"Title: {title}")
    print(f"Found {len(pages)} pages.")

    # 2. Check Images
    valid_images = 0
    for i, page in enumerate(pages):
        img_path = page.get('image_url', '')
        exists = os.path.exists(img_path) if img_path else False
        print(f"Page {i+1}: Image '{img_path}' -> Exists? {exists}")
        if exists:
            valid_images += 1

    print(f"Valid Images Found: {valid_images}/{len(pages)}")
    
    if valid_images == 0:
        print("CRITICAL: No valid images found. PDF generation will likely produce a valid but text-only PDF, or fail if image insertion is forced.")

    # 3. Attempt Minimal PDF Build
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    output_dir = os.path.join(root_path, "worker", "output", "images", TRAILHEAD_ID)
    pdf_path = os.path.join(output_dir, "DEBUG_Saga.pdf")
    
    print(f"Attempting to build debug PDF at: {pdf_path}")

    try:
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(letter),
            rightMargin=36, leftMargin=36,
            topMargin=36, bottomMargin=36
        )
        story = []
        styles = getSampleStyleSheet()
        story.append(Paragraph(f"DEBUG: {title}", styles['Heading1']))
        
        # Add just the first valid image
        if pages and pages[0].get('image_url') and os.path.exists(pages[0]['image_url']):
            img_path = pages[0]['image_url']
            try:
                img = PDFImage(img_path, width=4*inch, height=2.25*inch)
                story.append(img)
                print("Added first image to story.")
            except Exception as e:
                 print(f"Failed to add image object: {e}")

        doc.build(story)
        print("Debug PDF built successfully.")
        
    except Exception as e:
        print(f"Debug PDF Generation Failed: {e}")

if __name__ == "__main__":
    debug_pdf_generation()
