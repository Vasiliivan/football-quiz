def parse_questions(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    questions = []

    i = 0
    while i + 5 < len(lines):
        questions.append({
            "question": lines[i],
            "options": lines[i+1:i+5],
            "answer": lines[i+5].upper()
        })
        i += 6

    return questions
