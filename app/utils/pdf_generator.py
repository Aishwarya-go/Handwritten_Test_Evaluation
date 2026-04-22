import cv2
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import json
import os

# A4 dimensions in points (1 inch = 72 points)
PAGE_WIDTH, PAGE_HEIGHT = A4  # 595 x 842 points

MARGIN = 40
ARUCO_SIZE = 30  # size of ArUco marker in points
HEADER_HEIGHT = 80  # space for test title and student info

def generate_aruco_marker(marker_id, size_pixels=100):
    """Generate an ArUco marker image and return as numpy array"""
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_image = np.zeros((size_pixels, size_pixels), dtype=np.uint8)
    marker_image = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_pixels)
    return marker_image

def save_aruco_as_png(marker_id, path, size_pixels=100):
    """Save ArUco marker as PNG file temporarily"""
    marker = generate_aruco_marker(marker_id, size_pixels)
    cv2.imwrite(path, marker)

def generate_answer_sheet(test_id, title, questions, output_path):
    """
    Generate a PDF answer sheet with ArUco markers and question boxes.
    
    questions: list of dicts with keys:
        - question_number
        - question_text
        - max_marks
        - box_height (optional, default 120 points)
    
    Returns: list of bounding boxes per question (in points)
    """
    
    # Step 1: Generate 4 ArUco markers as temp PNG files
    aruco_paths = []
    for i in range(4):
        path = f"generated_pdfs/aruco_{test_id}_{i}.png"
        save_aruco_as_png(i, path)
        aruco_paths.append(path)
    
    # Step 2: Create PDF canvas
    c = canvas.Canvas(output_path, pagesize=A4)
    
    # Step 3: Draw ArUco markers at 4 corners
    # ReportLab origin is BOTTOM-LEFT, so we flip Y axis
    aruco_pt = ARUCO_SIZE + 5  # marker size in points
    
    # Top-left (marker 0)
    c.drawImage(aruco_paths[0], MARGIN, PAGE_HEIGHT - MARGIN - ARUCO_SIZE,
                width=ARUCO_SIZE, height=ARUCO_SIZE)
    # Top-right (marker 1)
    c.drawImage(aruco_paths[1], PAGE_WIDTH - MARGIN - ARUCO_SIZE,
                PAGE_HEIGHT - MARGIN - ARUCO_SIZE,
                width=ARUCO_SIZE, height=ARUCO_SIZE)
    # Bottom-left (marker 2)
    c.drawImage(aruco_paths[2], MARGIN, MARGIN,
                width=ARUCO_SIZE, height=ARUCO_SIZE)
    # Bottom-right (marker 3)
    c.drawImage(aruco_paths[3], PAGE_WIDTH - MARGIN - ARUCO_SIZE, MARGIN,
                width=ARUCO_SIZE, height=ARUCO_SIZE)
    
    # Step 4: Draw header
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - MARGIN - 15, title)
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN, PAGE_HEIGHT - MARGIN - 35, f"Test ID: {test_id}")
    c.drawString(MARGIN, PAGE_HEIGHT - MARGIN - 50, "Student Name: ___________________________")
    c.drawString(PAGE_WIDTH - 200, PAGE_HEIGHT - MARGIN - 50, "Roll No: ____________")
    
    # Divider line below header
    c.setStrokeColor(colors.black)
    c.line(MARGIN, PAGE_HEIGHT - MARGIN - 60,
           PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN - 60)
    
    # Step 5: Draw question boxes and collect bounding boxes
    bounding_boxes = []
    current_y = PAGE_HEIGHT - MARGIN - HEADER_HEIGHT  # start below header
    box_width = PAGE_WIDTH - 2 * MARGIN
    
    for q in questions:
        q_num = q["question_number"]
        q_text = q.get("question_text", f"Question {q_num}")
        max_marks = q["max_marks"]
        box_height = q.get("box_height", 120)
        
        # Check if box fits on current page, else add new page
        if current_y - box_height - 30 < MARGIN + ARUCO_SIZE + 10:
            c.showPage()
            current_y = PAGE_HEIGHT - MARGIN - 20
            # Redraw ArUco markers on new page
            for i, path in enumerate(aruco_paths):
                positions = [
                    (MARGIN, PAGE_HEIGHT - MARGIN - ARUCO_SIZE),
                    (PAGE_WIDTH - MARGIN - ARUCO_SIZE, PAGE_HEIGHT - MARGIN - ARUCO_SIZE),
                    (MARGIN, MARGIN),
                    (PAGE_WIDTH - MARGIN - ARUCO_SIZE, MARGIN)
                ]
                c.drawImage(path, positions[i][0], positions[i][1],
                           width=ARUCO_SIZE, height=ARUCO_SIZE)
        
        # Draw question label
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN, current_y - 12,
                    f"Q{q_num}. {q_text}  [{max_marks} marks]")
        
        # Draw answer box
        box_y = current_y - 15 - box_height
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.rect(MARGIN, box_y, box_width, box_height)
        
        # Store bounding box (x, y from top-left of page, width, height)
        # Convert ReportLab coords (bottom-left origin) to top-left origin
        bbox = {
            "question_number": q_num,
            "x": int(MARGIN),
            "y": int(PAGE_HEIGHT - (box_y + box_height)),  # flip to top-left origin
            "width": int(box_width),
            "height": int(box_height)
        }
        bounding_boxes.append(bbox)
        
        current_y = box_y - 15  # move down for next question
    
    c.save()
    
    # Cleanup temp ArUco PNG files
    for path in aruco_paths:
        if os.path.exists(path):
            os.remove(path)
    
    return bounding_boxes