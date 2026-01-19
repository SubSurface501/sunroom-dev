import streamlit as st
import os
import sys
import json
import subprocess
import platform

# Add current directory to path so we can import 'db'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.supabase_client import get_supabase_client

# --- Configuration ---
st.set_page_config(page_title="The Sun Room", layout="wide", page_icon="🌞")
db = get_supabase_client()

# --- Custom CSS for the "Book" Feel ---
st.markdown("""
<style>
    .narrative-text { 
        font-family: 'Georgia', serif; 
        font-size: 1.2rem; 
        line-height: 1.6; 
        color: #2c3e50; 
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #e67e22;
    }
    .metadata { font-size: 0.8rem; color: #7f8c8d; }
</style>
""", unsafe_allow_html=True)

# --- Helpers ---
def open_file(path):
    """Opens a file or folder in the OS default viewer."""
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":  # macOS
        subprocess.Popen(["open", path])
    else:  # Linux
        subprocess.Popen(["xdg-open", path])

def load_library(user_id):
    """Fetches all Storybook Trailheads."""
    response = db.table("Trailheads").select("*").eq("user_id", user_id).eq("type", "storybook_manifest").order("created_at", desc=True).execute()
    return response.data

# --- Main App ---
def main():
    st.sidebar.title("🌞 The Sun Room")
    
    # User Context (Hardcoded for your dev session)
    user_id = "57a5073f-6dc5-4b92-ad9b-925d01f8e88d" 
    
    # 1. The Library (Sidebar)
    st.sidebar.header("📚 Your Sagas")
    books = load_library(user_id)
    
    if not books:
        st.sidebar.warning("No books found. Run the Saga Agent!")
        return

    # Selection Logic
    book_titles = [b.get('title', 'Untitled') for b in books]
    selected_title = st.sidebar.radio("Select a Title:", book_titles)
    
    # Reset page index if book changes
    if 'last_selected_book' not in st.session_state:
        st.session_state.last_selected_book = selected_title
        
    if st.session_state.last_selected_book != selected_title:
        st.session_state.page_idx = 0
        st.session_state.last_selected_book = selected_title
    
    # Find the selected object
    selected_book = next((b for b in books if b.get('title') == selected_title), None)
    
    if selected_book:
        render_reader(selected_book)

def render_reader(book):
    manifest = book.get('content', {})
    trailhead_id = book.get('id')
    
    # --- Header Area ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(manifest.get('project_title', 'Untitled Saga'))
        st.caption(f"Narrated by: {manifest.get('narrator_voice_check', 'System')}")
    
    with col2:
        # The "Open PDF" Button
        # We reconstruct the path based on your output structure
        root_path = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(root_path, "worker", "output", "images", trailhead_id)
        
        st.write("") # Spacer
        if st.button("📂 Open Folder"):
            if os.path.exists(output_dir):
                open_file(output_dir)
            else:
                st.error("Output folder not found.")

    st.divider()

    # --- Concept Art Gallery ---
    with st.expander("🎨 Concept Art & Character Sheets", expanded=False):
        assets = manifest.get('asset_references', {})
        if assets:
            cols = st.columns(len(assets))
            for idx, (name, path) in enumerate(assets.items()):
                with cols[idx]:
                    if os.path.exists(path):
                        st.image(path, caption=name, use_container_width=True)
                    else:
                        st.warning(f"Missing: {name}")
        else:
            st.info("No concept art generated for this book.")

    # --- The Reader (Pagination) ---
    pages = manifest.get('pages', [])
    if not pages:
        st.error("This book has no pages.")
        return

    # Initialize Session State for Page Flipping
    if 'page_idx' not in st.session_state:
        st.session_state.page_idx = 0
        
    # Safety check: Ensure page_idx is valid for this book
    if st.session_state.page_idx >= len(pages):
        st.session_state.page_idx = 0
    
    # Pagination Controls
    p_prev, p_count, p_next = st.columns([1, 2, 1])
    
    with p_prev:
        if st.button("⬅️ Previous"):
            st.session_state.page_idx = max(0, st.session_state.page_idx - 1)
            
    with p_count:
        st.markdown(f"<h3 style='text-align: center;'>Page {st.session_state.page_idx + 1} / {len(pages)}</h3>", unsafe_allow_html=True)
        
    with p_next:
        if st.button("Next ➡️"):
            st.session_state.page_idx = min(len(pages) - 1, st.session_state.page_idx + 1)

    # --- Page Content ---
    current_page = pages[st.session_state.page_idx]
    
    # Layout: Image (Left/Top) vs Text (Right/Bottom)
    img_col, text_col = st.columns([1.5, 1])
    
    with img_col:
        img_path = current_page.get('image_url')
        if img_path and os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
        else:
            st.warning("Image pending or missing.")
            st.caption(f"Prompt: {current_page.get('visual_prompt')}")

    with text_col:
        st.markdown(f"<div class='narrative-text'>{current_page.get('narrative_text')}</div>", unsafe_allow_html=True)
        st.write("")
        st.info(f"👀 **Consistency Note:** {current_page.get('consistency_note', 'None')}")

if __name__ == "__main__":
    main()