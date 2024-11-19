from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
from PIL import Image as PILImage


class Report:
    def __init__(self):
        pass

    def test(self):
        print("Hello from Report")

    def create_report(self, save_path):
        # Create a PDF document with A4 size in landscape mode
        pdf_file = "example.pdf"
        doc = SimpleDocTemplate(save_path, pagesize=landscape(A4), leftMargin=50, rightMargin=50, topMargin=30,
                                bottomMargin=50)

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name='TitleLeftAligned',
            fontName='Helvetica-Bold',  # Correct font name for bold
            fontSize=16,
            alignment=0,  # 0 = left aligned
            spaceAfter=12
        )
        # normal_style = styles['BodyText']

        # Title and content
        title = Paragraph("MEASUREMENT REPORT", title_style)
        # content = Paragraph("content", normal_style)

        # Path to the image (replace 'your_image.png' with your image path)
        image_path = 'logo-LAB-motion-systems.png'
        image = Image(image_path, width=92, height=50)  # Adjust the image size as needed

        current_date = datetime.now().strftime("%d-%m-%Y")
        # Define the table data
        data = [
            ['Leuven Air Bearing NV', 'www.leuvenairbearings.com', f'Date: {current_date}', image],
            ['Langerode 9', 'info@leuvenairbearings.com', '', ''],
            ['3460 Bekkevoort', '+32 13 29 40 35', '', '']
        ]

        # Create a table with full page width
        table = Table(data, colWidths=[(doc.width - 116.0) / 3] * 3 + [
            116])  # Set the column widths, adjust the last column width for the image

        # Apply table styling
        table.setStyle(TableStyle([
            ('SPAN', (3, 0), (3, 2)),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (-2, -1), colors.black),
            ('ALIGN', (0, 0), (-2, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 0, colors.white),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ]))

        plot_path = 'temp_plot.png'
        with PILImage.open(plot_path) as img:
            img_width, img_height = img.size
        aspect_ratio = img_width / img_height
        max_width = doc.width
        max_height = doc.height - 200

        if img_width > max_width or img_height > max_height:
            if (max_width / img_width) < (max_height / img_height):
                img_width = max_width
                img_height = max_width / aspect_ratio
            else:
                img_height = max_height
                img_width = max_height * aspect_ratio

        plot_image = Image(plot_path, height=img_height, width=img_width)
        # Combine elements into a story
        story = [table, Spacer(1, 20), title, Spacer(1, 20), plot_image]

        # Build the PDF
        doc.build(story)

        print(f"PDF created successfully: {pdf_file}")
