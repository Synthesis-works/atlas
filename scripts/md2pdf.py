import sys
from markdown_pdf import MarkdownPdf, Section

def main():
    if len(sys.argv) < 3:
        print("Usage: py md2pdf.py <input.md> <output.pdf>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    with open(input_file, "r", encoding="utf-8") as f:
        md_text = f.read()
        
    pdf = MarkdownPdf()
    pdf.add_section(Section(md_text, toc=False))
    pdf.save(output_file)
    print(f"Saved PDF to {output_file}")

if __name__ == "__main__":
    main()
