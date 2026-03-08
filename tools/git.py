import subprocess

def git_status():
    result = subprocess.run(
        ["git", "status"],
        capture_output=True,
        text=True
    )

    return result.stdout


def git_diff():
    result = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True
    )

    return result.stdout
