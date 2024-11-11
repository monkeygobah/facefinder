import tkinter as tk
from tkinter import filedialog, font
import os
from facefinder_2 import threaded_main_loop
import threading

stop_event = threading.Event()


def run_face_detection():
    home_directory = directory_entry.get()
    data_good = data_good_entry.get()
    data_bad = data_bad_entry.get()
    eye_min_neighbors = int(eye_min_neighbors_var.get())
    face_min_neighbors = int(face_min_neighbors_var.get())

    # Create directories if they don't exist
    for path in [data_good, data_bad]:
        if not os.path.exists(path):
            os.makedirs(path)
    
    
    def check_thread():
        if processing_thread.is_alive():
            # Thread is still running, check again after some time
            root.after(100, check_thread)
        else:
            on_thread_finished()
            
    
    def on_thread_finished():
        if not stop_event.is_set():
            feedback_label.config(text="Processing finished.")
        stop_event.clear()  # Reset the stop event for the next run
            
    # Call your main loop function
    processing_thread = threading.Thread(target=threaded_main_loop, args=(home_directory, data_good, data_bad,stop_event, eye_min_neighbors, face_min_neighbors))
    processing_thread.start()
    check_thread()
    
    # # Wait for the thread to finish and then update the feedback label
    # processing_thread.join()
    # on_thread_finished()
    
    # Provide feedback, such as a popup message
def stop_processing():
    feedback_label.config(text="Processing stopped.")

    stop_event.set()

def select_directory():
    directory = filedialog.askdirectory()
    directory_entry.delete(0, tk.END)
    directory_entry.insert(0, directory)

root = tk.Tk()
root.title("FaceFinder")  # Set the title of the window

feedback_label = tk.Label(root, text="")
feedback_label.pack()

# Define a bold font
bold_font = font.Font(weight="bold")

# Home directory input
tk.Label(root, text="Home Directory:",  font=bold_font).pack()
directory_entry = tk.Entry(root, width=50)
directory_entry.pack()

select_button = tk.Button(root, text="Select Directory", font=bold_font, command=select_directory)
select_button.pack()

# Data good directory input
tk.Label(root, text="Good Data Directory:", font=bold_font).pack()
data_good_entry = tk.Entry(root, width=50)
data_good_entry.pack()

# Data bad directory input
tk.Label(root, text="Bad Data Directory:", font=bold_font).pack()
data_bad_entry = tk.Entry(root, width=50)
data_bad_entry.pack()

# Eye Min Neighbors dropdown
tk.Label(root, text="Eye Min Neighbors:", font=bold_font).pack()
eye_min_neighbors_var = tk.StringVar(root)
eye_min_neighbors_var.set("8")  # default value
eye_min_neighbors_menu = tk.OptionMenu(root, eye_min_neighbors_var, "0", "1", "2", "3", "4", "5", "6", "7", "8")
eye_min_neighbors_menu.pack()

# Face Min Neighbors dropdown
tk.Label(root, text="Face Min Neighbors:", font=bold_font).pack()
face_min_neighbors_var = tk.StringVar(root)
face_min_neighbors_var.set("0")  # default value
face_min_neighbors_menu = tk.OptionMenu(root, face_min_neighbors_var, "0", "1", "2", "3", "4", "5", "6", "7", "8")
face_min_neighbors_menu.pack()

# Stop Button
stop_button = tk.Button(root, text="Stop Processing", command=stop_processing)
stop_button.pack()

# Run button
run_button = tk.Button(root, text="Run FaceFinder", font=bold_font, command=run_face_detection)
run_button.pack()

root.mainloop()
