import fitz
import sys

def read_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = ""
        # Read first 10 pages or all if less
        for i in range(min(10, len(doc))):
            text += doc[i].get_text()
        print(text)
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        read_pdf(sys.argv[1])
    else:
        print("Please provide a file path.")
