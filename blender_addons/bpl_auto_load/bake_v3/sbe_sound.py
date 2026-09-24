import os

is_windows = False
if os.name == 'nt':
    try:
        import winsound
        is_windows = True
    except:
        is_windows = False

def error_sound():
    try:
        if is_windows:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
        else:
            os.system("play -nq -t alsa synth 0.3 sine 220")
    except:
        print("Failed to play error sound")
def success_sound():
    try:
        if is_windows:
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
        else:
            os.system("play -nq -t alsa synth 0.3 sine 440")
    except:
        print("Failed to play error sound")
