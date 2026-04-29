#### create tools
import subprocess
import datetime

## helper


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()



## tools


import subprocess
import time


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def open_app(app_name: str, x: int = 100, y: int = 100, width: int = 1200, height: int = 800, window_index: int = 1) -> None:
    """
    Open an app and place its window.
    """

    banned_apps = {
        "Dock",
        "Control Center",
        "Notification Center",
        "SystemUIServer",
    }
    if app_name in banned_apps:
        raise ValueError(f"{app_name} is not supported for window control.")

    subprocess.run(["open", "-a", app_name], check=True)

    # give the app time to launch and create a window
    for _ in range(20):
        try:
            move_resize_app(app_name, x, y, width, height, window_index=window_index)
            return
        except Exception:
            time.sleep(0.25)

    raise RuntimeError(f"Opened {app_name}, but could not find a controllable window.")





def open_url(url: str) -> None:
    subprocess.run(['open', url], check = True)

def list_running_apps() -> list[str]:
    script = '''
    tell application "System Events"
        set appList to name of every application process whose background only is false
        set AppleScript's text item delimiters to linefeed
        return appList as text
    end tell
    '''
    output = run_applescript(script)
    return [x.strip() for x in output.splitlines() if x.strip()]

def get_frontmost_app() -> str:
    script = '''
    tell application "System Events"
        set frontApp to name of first application process whose frontmost is true
        return frontApp
    end tell
    '''
    return run_applescript(script)




def get_weather():
    return None


def get_datetime():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")



def get_all_installed_apps():
    script = '''
    tell application "Finder"
        set appList to name of every application file in (path to applications folder)
        set AppleScript's text item delimiters to linefeed
        return appList as text
    end tell
    '''
    output = run_applescript(script)
    return [x.strip() for x in output.splitlines() if x.strip()]
    



def get_battery():
    battery = subprocess.run(
        ["pmset", "-g", "batt"],
        capture_output=True,
        text=True,
        check=True
    ).stdout
    return battery.strip()


def notify(title: str, message: str) -> None:
    script = f'''
    display notification "{message}" with title "{title}"
    '''
    subprocess.run(["osascript", "-e", script], check=True)


def schedule_notification(title: str, message: str, time: str) -> None:
    # time should be in format "HH:MM"
    script = f'''
    do shell script "echo 'display notification \\"{message}\\" with title \\"{title}\\"' | at {time}"
    '''
    subprocess.run(["osascript", "-e", script], check=True)

def close_app(app_name: str) -> None:
    script = f'''
    tell application "{app_name}"
        quit
    end tell
    '''
    run_applescript(script)


def empty_trash() -> None:
    script = '''
    tell application "Finder"
        empty the trash
    end tell
    '''
    run_applescript(script)


## context

def build_computer_state() -> str:
    front_app = get_frontmost_app()
    date = get_datetime()
    battery = get_battery()
    running_apps = list_running_apps()
    installed_apps = get_all_installed_apps()
    state = f"Frontmost app: {front_app}\nRunning apps: {', '.join(running_apps)} + Date: {date} + Battery: {battery} + Installed apps: {', '.join(installed_apps)}"
    return state




## spawning subagents


#### For speed ups, it needs to not write the memory. The memory should be a persistant thing added to via a tool call....




## this is meant for more complex tasks.... the idea is that the main agent can spawn sub-agents to handle specific tasks, and then the main agent can feed the results back into the context for future reasoning. this is a bit more complex than just calling a tool, because it allows for more complex interactions and reasoning within the sub-agent, and then feeding that back into the main agent's context.

