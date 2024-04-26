import re

auto_responses = {
r"join|download|how(.*)play": """It looks like you're trying to download our launcher!
You can download the launcher from here:
                
https://mcnations.org/
    
Once downloading, you have to extract the zip file, and go to Nations Launcher Setup and then you can launch.
You can disable this notification by using -download disable""",
r"(?:[^a-zA-Z]|^)ip(?:[^a-zA-Z]|$)": "The IP to the server is: play.mcnations.org"
}

def compile_regex(auto_responses):
    formatted = dict()
    for regex, response in auto_responses.items():
        compiled = re.compile(regex, re.IGNORECASE)
        formatted[compiled] = response
    return formatted

auto_responses = compile_regex(auto_responses)