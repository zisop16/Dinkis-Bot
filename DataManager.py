from pymongo import MongoClient
import time

class DataManager:
    def __init__(self, password):
        api_url = f"mongodb+srv://p0six:{password}@cluster0.e7vueuh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        cluster = MongoClient(api_url)
        db = cluster["NationsDiscord"]
        self.user_data = db["UserData"]
        self.server_data = db["ServerData"]
    
    def get_user(self, user_id):
        result = self.user_data.find_one({"_id": user_id})
        return result
    
    def user_exists(self, user_id):
        return self.get_user(user_id) is not None
    
    def add_user(self, user_id):
        post = {
            "_id": user_id,
            "warnings": 0,
            # Time in UNIX of last staff application
            "last_application": 0
        }
        self.user_data.insert_one(post)

    def reset_application_timer(self, user_id):
        self.safe_add(user_id)
        query = {"_id": user_id}
        command = {
            "$set": {
                "last_application": time.time()
            }
        }

    def can_apply(self, user_id):
        data = self.get_user(user_id)
        last_application = data["last_application"]
        delay = time.time() - last_application
        three_months = 60 * 60 * 24 * 30
        return delay > three_months

    def add_warning(self, user_id):
        query = {"_id": user_id}
        command = {
            "$inc": {
                "warnings": 1
            }
        }
        self.user_data.update_one(query, command)

    def get_warnings(self, user_id):
        data = self.get_user(user_id)
        warnings = data["warnings"]
        return warnings

    def safe_add(self, user_id):
        if not self.get_user(user_id):
            self.add_user(user_id)