users = {}

def get_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "questions": [],
            "index": 0,
            "score": 0,
            "active": False
        }
    return users[user_id]
