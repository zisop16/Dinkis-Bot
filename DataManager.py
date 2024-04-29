from pymongo import MongoClient
import time
import datetime

class DataManager:
    
    def __init__(self, username, password):
        api_url = f"mongodb+srv://{username}:{password}@cluster0.e7vueuh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        cluster = MongoClient(api_url)
        db = cluster["NationsDiscord"]
        self.user_data = db["UserData"]
        self.server_data = db["ServerData"]
    
    def get_user(self, user_id):
        self.safe_add(user_id)
        result = self.user_data.find_one({"_id": user_id})
        return result
    
    def user_exists(self, user_id):
        return self.get_user(user_id) is not None
    
    def add_user(self, user_id):
        post = {
            "_id": user_id,
            "warnings": 0,
            # Time in UNIX of last staff application
            "last_application": 0,
            "allow_help": True
        }
        self.user_data.insert_one(post)

    def set_help_wishes(self, user_id, setting: bool):
        query = {"_id": user_id}
        command = {
            "$set": {
                "allow_help": setting
            }
        }
        self.user_data.update_one(query, command)

    def wants_help(self, user_id):
        return self.get_user(user_id)["allow_help"]

    def reset_application_timer(self, user_id):
        self.safe_add(user_id)
        query = {"_id": user_id}
        command = {
            "$set": {
                "last_application": time.time()
            }
        }
        self.user_data.update_one(query, command)

    def remaining_application_time(self, user_id):
        data = self.get_user(user_id)
        last_application = data["last_application"]
        delay = time.time() - last_application
        delay = datetime.timedelta(seconds=delay)
        three_months = datetime.timedelta(days=30)
        return three_months - delay

    def add_warning(self, user_id):
        self.safe_add(user_id)
        query = {"_id": user_id}
        command = {
            "$inc": {
                "warnings": 1
            }
        }
        self.user_data.update_one(query, command)

    def remove_warning(self, user_id):
        self.safe_add(user_id)
        query = {"_id": user_id}
        command = {
            "$inc": {
                "warnings": -1
            }
        }
        self.user_data.update_one(query, command)

    def reset_warnings(self, user_id):
        self.safe_add(user_id)
        query = {"_id": user_id}
        command = {
            "$set": {
                "warnings": 0
            }
        }
        self.user_data.update_one(query, command)

    def get_warnings(self, user_id):
        data = self.get_user(user_id)
        warnings = data["warnings"]
        return warnings

    def safe_add(self, user_id):
        if not self.user_data.find_one({"_id": user_id}):
            self.add_user(user_id)

manager: DataManager = None