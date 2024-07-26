from tkinter import Tk, Label, Button, Listbox, Scrollbar, Frame, Toplevel, Entry
from tkinter import END, LEFT, RIGHT, TOP
from tkinter.ttk import Notebook

from threading import Thread
import time, os, shutil

import pyaudio, wave

import random as rng, string


class Recorder:
    """
    Represents an instance of the application.
    """
    def __init__(self) -> None:
        """
        Initializes an instance of the recorder application. Sets up the
        UI elements and class attributes.
        """
        # tkinter window setup
        self.root: Tk = Tk()
        self.root.geometry("300x200+500+200")
        self.root.resizable(False, False)
        self.root.title("Voice Recorder")

        # set fonts and colors
        self.TIMER_FONT: str = "Helvetica"
        self.TEXT_FONT: str = "Courier New"
        self.BUTTON_FONT: str = "Courier New"

        self.bg_color: str = "#ddd"

        ## UI ELEMENTS
        # tabs
        self.tabs: Notebook = Notebook(self.root)

        self.record_audio_tab: Frame = Frame(self.root)
        self.play_audio_tab: Frame = Frame(self.root)

        self.tabs.add(self.record_audio_tab, text="Record Audio")
        self.tabs.add(self.play_audio_tab, text="Play Audio")

        self.tabs.pack(expand=1, fill="both")

        def tab_selected(event) -> None:
            self.root.focus()

        self.tabs.bind('<<NotebookTabChanged>>', tab_selected)

        # record_audio_tab ui elements
        self.record_audio_tab.config(background=self.bg_color)

        self.timer_text: Label = Label(self.record_audio_tab, text="00:00:00",
                                       font=(self.TIMER_FONT, 30),
                                       background=self.bg_color)
        self.timer_text.place(relx=0.5, rely=0.25, anchor="center")

        self.recording_indicator: Label = Label(self.record_audio_tab,
                                                text="*RECORDING*",
                                                font=(self.TEXT_FONT, 10),
                                                foreground="grey",
                                                background=self.bg_color)
        self.recording_indicator.place(relx=0.5, rely=0.5, anchor="center")

        self.start_button: Button = Button(self.record_audio_tab, text="Start",
                                           font=(self.BUTTON_FONT, 8),
                                           width=7,
                                           command=self.start_recording)
        self.start_button.place(relx=0.2, rely=0.75, anchor="center")

        self.reset_button: Button = Button(self.record_audio_tab, text="Reset",
                                           font=(self.BUTTON_FONT, 8),
                                            width=7,
                                             command=self.reset_recording)
        self.reset_button.place(relx=0.5, rely=0.75, anchor="center")

        self.stop_button: Button = Button(self.record_audio_tab, text="Stop",
                                          font=(self.BUTTON_FONT, 8),
                                          width=7,
                                          command=self.stop_recording)
        self.stop_button.place(relx=0.8, rely=0.75, anchor="center")

        # record_audio_tab data and attributes
        self.recording_audio: bool = False
        self.recording_audio_paused: bool =False
        self.reset: bool = False
        self.current_time: int = 0 # microseconds
        
        self.recordings: list[str] = []

        # play_audio_tab ui elements
        self.play_audio_tab.config(background=self.bg_color)

        # header
        self.title_and_selection: Frame = Frame(self.play_audio_tab,
                                                background=self.bg_color)
        
        self.current_audio_selection: Label = Label(self.title_and_selection,
                                                    text="",
                                                    font=(self.TEXT_FONT, 11),
                                                    background=self.bg_color)
        self.current_audio_selection.pack(side=LEFT, padx=5)

        self.title_and_selection.pack(side=TOP, fill="x")

        # audio list
        self.recording_listbox: Listbox = Listbox(self.play_audio_tab,
                                                  relief="sunken",
                                                  width=31, height=10)
        self.recording_listbox.pack(side=LEFT, padx=(5, 0), pady=5)

        # scrollbar
        self.scrollbar: Scrollbar = Scrollbar(self.play_audio_tab)
        self.scrollbar.pack(side=RIGHT, fill="both")

        # buttons
        self.buttons: Frame = Frame(self.play_audio_tab, 
                                    background=self.bg_color)
        
        self.play_button: Button = Button(self.buttons, text="Play",
                                          font=(self.BUTTON_FONT, 9),
                                          width=10,
                                          command=self.play_recording)
        self.play_button.pack(padx=5, pady=0)

        self.pause_button: Button = Button(self.buttons, text="Pause",
                                           font=(self.BUTTON_FONT, 9),
                                           width=10,
                                           command=self.pause_recording)
        self.pause_button.pack(padx=5, pady=1)

        self.rename_button: Button = Button(self.buttons, text="Rename",
                                            font=(self.BUTTON_FONT, 9),
                                            width=10,
                                            command=self.rename_recording)
        self.rename_button.pack(padx=5, pady=1)

        self.delete_button: Button = Button(self.buttons, text="Delete", 
                                            font=(self.BUTTON_FONT, 9),
                                            width=10,
                                            command=self.delete_recording)
        self.delete_button.pack(padx=5, pady=1)

        self.clear_all_button: Button = Button(self.buttons, text="DEL ALL",
                                               font=(self.BUTTON_FONT, 9),
                                               width=10,
                                               foreground="red",
                                               command=self.delete_all_recordings)
        self.clear_all_button.pack(padx=5, pady=(10, 0))

        self.buttons.pack(side=RIGHT, fill='y', padx=5, pady=5)

        # connect recording listbox and scrollbar
        self.recording_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.recording_listbox.yview)

        self.current_audio: str = ""

        def on_listbox_select(event) -> None:
            try:
                index: int = int(event.widget.curselection()[0])
                value: str = event.widget.get(index)
                self.current_audio = value
                
                self.current_audio_selection.config(text=self.current_audio)
            except IndexError:
                pass

        self.recording_listbox.bind('<<ListboxSelect>>', on_listbox_select)

        # play_audio_tab data and attributes
        self.current_replay: str = ""
        self.playing_audio: bool = False
        self.playing_audio_paused: bool = False

        # ensure audio folder exists and set recordings list
        self.sort_audio_recordings()
        self.update_recording_listbox()

        self.root.mainloop()


    def sort_audio_recordings(self) -> None:
        """
        Sort the files in the audio_recordings folder in descending order
        acording to their date of creation and store them in the recordings
        list. Create the folder if it doesn't exist.
        """
        while True:
            try:
                files: list[str] = []
                for audio_file in os.listdir("./audio_recordings"):
                    files.append(audio_file)

                files.sort(key=lambda path: \
                           os.stat(f"audio_recordings/{path}").st_ctime)
                
                self.recordings = files
                break
            except FileNotFoundError:
                os.makedirs("audio_recordings")


    def start_recording(self) -> None:
        """
        Start the timer and audio recording threads.
        """
        # stop any audio playback
        self.playing_audio = False

        if self.recording_audio:
            # pause audio recording
            self.recording_audio = False
            self.recording_audio_paused = True

            # update ui elements
            self.recording_indicator.config(foreground="grey")
            self.start_button.config(text="Start")
            self.root.title("Voice Recorder")
        else:
            # start/continue recording audio
            self.recording_audio = True

            # only start a new set of threads when not dealing with an 
            # ongoing, paused recording
            if not self.recording_audio_paused:
                self.recording_audio_paused = True

                # start new audio thread
                audio_thread: Thread = Thread(target=self.start_audio)
                audio_thread.daemon = True
                audio_thread.start()

                # start new timer thread
                timer_thread: Thread = Thread(target=self.start_timer)
                timer_thread.daemon = True
                timer_thread.start()
            else:
                self.recording_audio_paused = False

            # update ui elements
            self.recording_indicator.config(foreground="red")
            self.start_button.config(text="Pause")
            self.root.title("RECORDING...")

    
    def update_timer_text(self, mins: int, secs: int, micros: int) -> None:
        """
        Update the timer ui with the given hour, second and microsecond 
        values.

        :param mins: number of minutes
        :param secs: number of seconds
        :param micros: number of microseconds
        """
        formatted_text: str = f"{mins:02d}:{secs:02d}:{micros:02d}"
        self.timer_text.config(text=formatted_text)


    def start_timer(self) -> None:
        """
        Start the recording timer.
        """
        minutes, seconds, microseconds = 0, 0, 0

        while True:
            # run timer
            while self.recording_audio:
                seconds, microseconds = divmod(self.current_time, 100)
                minutes, seconds = divmod(seconds, 60)

                self.update_timer_text(minutes, seconds, microseconds)

                time.sleep(0.01)
                self.current_time += 1

            # pause timer
            while self.recording_audio_paused:
                time.sleep(0.001)

            # stop timer
            if not (self.recording_audio or self.recording_audio_paused):
                break
            

    def generate_temporary_file_name(self) -> str:
        """
        Generate a random temporary file name.

        :return: a 12 digit long file name.
        """
        chars: list[str] = rng.choices(string.digits, k=12)
        name: str = ''.join(chars)
        return name
    

    def start_audio(self) -> None:
        """
        Start recording audio.
        """
        # record audio frames
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16, channels=1, rate=44100,
                            input=True, frames_per_buffer=1024)
        
        frames: list[bytes] = list()

        while True:
            # record audio
            while self.recording_audio:
                data: bytes = stream.read(1024)
                frames.append(data)

            # pause recording
            while self.recording_audio_paused:
                time.sleep(0.001)

            # stop recording
            if not (self.recording_audio or self.recording_audio_paused):
                break
        
        stream.stop_stream()
        stream.close()
        audio.terminate()

        # do not save the file if the reset button was hit
        if self.reset:
            self.reset = False
            return

        # create temporary file to store the audio
        temp_file_name: str = f"{self.generate_temporary_file_name()}.wav"

        # ensure the name is unique
        while temp_file_name in self.recordings:
            temp_file_name = f"{self.generate_temporary_file_name()}.wav"

        # write audio frames to the file
        sound_file: wave.Wave_write = wave.open(temp_file_name, "wb")
        sound_file.setnchannels(1)
        sound_file.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        sound_file.setframerate(44100)
        sound_file.writeframes(b''.join(frames))
        sound_file.close()

        self.recordings.append(temp_file_name)


    def reset_recording(self) -> None:
        """
        Reset the recording.
        """
        # button should be inactive if not recording or paused
        if not(self.recording_audio or self.recording_audio_paused):
            return
        
        # pause recording
        self.recording_audio = False
        self.recording_audio_paused = True
        self.start_button.config(text="Start")
        self.recording_indicator.config(foreground="grey")
        self.root.title("Voice Recording")
        
        # confirm reset
        confirm: bool = self.confirm_reset()

        # exit the function if the player cancels
        if not confirm:
            return
        
        # unpause and reset the recording
        self.reset = True
        self.recording_audio_paused = False

        # reset timer and update ui elements
        self.update_timer_text(0, 0, 0)
        self.current_time = 0

        self.recording_indicator.config(foreground="grey")    
        self.start_button.config(text="Start")


    def confirm_reset(self) -> bool:
        """
        Confirm whether the recording should be reset.

        :return: True -> reset recording, False -> cancel reset.
        """
        menu: Toplevel = Toplevel()

        root_geometry: str = self.root.wm_geometry(None)

        root_width: int = int(root_geometry.split('x')[0])
        root_height: int = int(root_geometry.split('+')[0].split('x')[1])

        menu_width: int = 200
        menu_height: int = 100

        posx: int = int(root_geometry.split('+')[1]) + \
            ((root_width - menu_width) // 2)
        posy: int = int(root_geometry.split('+')[2]) + \
            ((root_height - menu_height) // 2)
        menu.geometry(f"{menu_width}x{menu_height}+{posx}+{posy}")

        menu.resizable(False, False)
        menu.title("Confirm Reset")
        menu.config(background=self.bg_color)
        menu.grab_set()

        warning_label: Label = Label(menu, text="Reset Recording?",
                                     font=(self.TEXT_FONT, 11),
                                     background=self.bg_color)
        warning_label.place(relx=0.5, rely=0.3, anchor="center")

        self.confirm: bool = False

        def reset_audio() -> None:
            # confirm audio reset
            self.confirm = True
            menu.destroy()

        def cancel() -> None:
            # set audio reset to false
            self.confirm = False
            menu.destroy()

        reset_button: Button = Button(menu, text="Reset", 
                                      font=(self.BUTTON_FONT, 8),
                                      width=8,
                                      command=reset_audio)
        reset_button.place(relx=0.3, rely=0.7, anchor="center")

        cancel_button: Button = Button(menu, text="Cancel",
                                       font=(self.BUTTON_FONT, 8),
                                       width=8,
                                       command=cancel)
        cancel_button.place(relx=0.7, rely=0.7, anchor="center")


        self.root.wait_window(menu)

        return self.confirm
                                     

    def stop_recording(self) -> None:
        """
        Stop recording and save the audio file to the appropriate folder.
        """
        # button should be inactive whilst not recording any audio
        if not (self.recording_audio or self.recording_audio_paused):
            return

        # pause recording
        self.recording_audio = False
        self.recording_audio_paused = True

        self.recording_indicator.config(foreground="grey")
        self.start_button.config(text="Start")
        self.root.title("Voice Recorder")

        # launch save recording pop-up menu and get recording title
        save_title: str = self.save_recording_menu()

        if save_title:
            # stop the recording
            self.recording_audio_paused = False

            # reset timer and update ui elements
            self.update_timer_text(0, 0, 0)
            self.current_time = 0

            # change file name
            time.sleep(0.5)

            recording: str = self.recordings[-1]
            os.rename(recording, f"{save_title}.wav")
            recording = f"{save_title}.wav"
            self.recordings = self.recordings[:-1] + [recording]

            # store file in the appropriate folder
            self.move_audio_to_file(recording)

            # update recording listbox
            self.update_recording_listbox()

            # if there is no selected audio, update ui accordingly
            if not self.current_replay:
                self.current_audio = ""
                self.current_audio_selection.config(text=self.current_audio)


    def move_audio_to_file(self, filename: str) -> None:
        """
        Move an audio file from the current root directory to the 
        audio_recordings folder.

        :param filename: the audio file to be relocated.
        """
        # get the current location of the module and remove the program name
        # current_path: str = __file__.replace("VoiceRecorder.py", '')
        ### this method can adapt if the name of the program file is changed
        current_path: str = ''.join(__file__.split("/")[:-1])

        # get the location of the audio storage folder, create a folder if none exists
        audio_folder_path: str = current_path + "audio_recordings"
        if not os.path.exists(audio_folder_path):
            os.makedirs(audio_folder_path)

        # move the audio recording to the folder
        current_audio_path: str = current_path + filename
        destination_audio_path: str = audio_folder_path + f"\\{filename}"
        shutil.move(current_audio_path, destination_audio_path)
        
        
    def save_recording_menu(self) -> str:
        """
        Launch a pop-up window to save the recording with a certain filename.

        :return: the target filename, an empty string implies the save was
        canceled.
        """
        # ui elements
        menu: Toplevel = Toplevel()

        root_geometry: str = self.root.wm_geometry(None)

        root_width: int = int(root_geometry.split('x')[0])
        root_height: int = int(root_geometry.split('+')[0].split('x')[1])

        menu_width: int = 260
        menu_height: int = 100

        posx: int = int(root_geometry.split('+')[1]) + \
            ((root_width - menu_width) // 2)
        posy: int = int(root_geometry.split('+')[2]) + \
            ((root_height - menu_height) // 2)
        menu.geometry(f"{menu_width}x{menu_height}+{posx}+{posy}")

        menu.resizable(False, False)
        menu.title("Save Recording")
        menu.config(background=self.bg_color)
        menu.grab_set()

        self.title: str = ""

        entry_label: Label = Label(menu, text="Title: ",
                                   font=(self.TEXT_FONT, 10),
                                   background=self.bg_color)
        entry_label.place(relx=0.15, rely=0.25, anchor="center")

        def validate(P):
            if len(P) == 0:
                return True
            elif len(P) <= 23:
                return True
            else:
                return False 
            
        vcmd = (menu.register(validate), '%P')

        title_entry: Entry = Entry(menu, font=(self.TEXT_FONT, 10),
                                   validate="all",
                                   validatecommand=vcmd)
        title_entry.place(relx=0.6, rely=0.25, anchor="center")
        title_entry.focus()

        warning_text: Label = Label(menu, text="",
                                    font=(self.TEXT_FONT, 8),
                                    background=self.bg_color,
                                    foreground="red")
        warning_text.place(relx=0.28, rely=0.45, anchor="w")

        def save_file() -> None:
            # save the audio file to the root directory with the given name
            given_name: str = title_entry.get().replace('.wav', '')

            if f"{given_name}.wav" in self.recordings:
                warning_text.config(text="*file name taken")
            elif given_name == "":
                warning_text.config(text="*enter a file name")
            else:
                self.title = given_name
                menu.destroy()

        def cancel_save() -> None:
            # cancel save
            menu.destroy()

        save_button: Button = Button(menu, text="Save",
                                     font=(self.BUTTON_FONT, 8),
                                     width=7,
                                     command=save_file)
        save_button.place(relx=0.3, rely=0.72, anchor="center")

        cancel_button: Button = Button(menu, text="Cancel",
                                       font=(self.BUTTON_FONT, 8),
                                       width=7,
                                       command=cancel_save)
        cancel_button.place(relx=0.7, rely=0.72, anchor="center")

        self.root.wait_window(menu)
        
        return self.title


    def update_recording_listbox(self) -> None:
        """
        Update the listbox UI with the current set of recordings.
        """
        self.sort_audio_recordings()
        self.recording_listbox.delete(0, END)

        for audio_file in self.recordings:
            self.recording_listbox.insert(0, audio_file)


    def play_recording(self) -> None:
        """
        Play the selected audio recording in a separate thread.
        """
        if self.recording_audio:
            return 
        
        try:
            recording_index: int = self.recording_listbox.curselection()[0]
        except IndexError:
            return
        
        if self.current_replay:
            # stop
            self.current_replay = ""
            self.playing_audio = False
            self.playing_audio_paused = False
            self.play_button.config(text="Play")
            self.pause_button.config(text="Pause")
            self.current_audio_selection.config(text=self.current_audio)
        else:
            # start
            self.playing_audio_paused = False
            replay_thread: Thread = Thread(target=self.play_audio)
            replay_thread.daemon = True
            replay_thread.start()
            self.play_button.config(text="Stop")
        
        
    def play_audio(self) -> None:
        """
        Play an audio recording.
        """
        recording_index: int = self.recording_listbox.curselection()[0]
        recording: str = self.recording_listbox.get(recording_index)
        self.current_replay = recording
        recording_path: str = f"audio_recordings/{recording}"

        CHUNK: int = 1024

        with wave.open(recording_path, "rb") as wf:
            audio = pyaudio.PyAudio()

            stream = audio.open(format=audio.get_format_from_width(wf.getsampwidth()),
                                channels=wf.getnchannels(),
                                rate=wf.getframerate(),
                                output=True)
            
            self.playing_audio = True
            self.root.title(f"Playing: {recording}")

            while self.current_replay:
                # play audio
                while len(data := wf.readframes(CHUNK)) and self.playing_audio:
                    stream.write(data)

                # break the loop if the recording has reached the end
                if not len(data): break

                # pause audio
                while self.playing_audio_paused:
                    time.sleep(0.001)
            
        stream.close()
        audio.terminate()

        self.root.title("Voice Recorder")
        self.playing_audio = False
        self.current_replay = ""
        self.play_button.config(text="Play")
            
    
    def pause_recording(self) -> None:
        """
        Pause the current audio recording.
        """
        if self.recording_audio or not self.current_replay:
            return

        if self.playing_audio_paused:
            # resume
            self.playing_audio = True
            self.playing_audio_paused = False
            self.current_audio_selection.config(text=self.current_replay)
            self.root.title(f"Playing: {self.current_replay}")
            self.pause_button.config(text="Pause")
        else:
            # pause
            self.playing_audio = False
            self.playing_audio_paused = True
            current: str = self.current_replay
            self.current_audio_selection.config(text=f"{current}(paused)")
            self.root.title("Voice Recorder")
            self.pause_button.config(text="Resume")

    
    def rename_recording(self) -> None:
        """
        Rename the selected audio recording.
        """
        try:
            index: int = self.recording_listbox.curselection()[0]
            current_name = self.recording_listbox.get(index)
        except IndexError:
            return

        if self.recording_audio:
            return
        
        if current_name == self.current_replay:
            # pause audio
            self.playing_audio = False
            self.playing_audio_paused = True
            self.pause_button.config(text="Resume")
            current: str = self.current_replay
            self.current_audio_selection.config(text=f"{current}(paused)")
            self.root.title("Voice Recorder")

        # create and launch a pop-up window to rename the recording
        menu: Toplevel = Toplevel()
        
        root_geometry: str = self.root.wm_geometry(None)

        root_width: int = int(root_geometry.split('x')[0])
        root_height: int = int(root_geometry.split('+')[0].split('x')[1])

        menu_width: int = 260
        menu_height: int = 100

        posx: int = int(root_geometry.split('+')[1]) + \
            ((root_width - menu_width) // 2)
        posy: int = int(root_geometry.split('+')[2]) + \
            ((root_height - menu_height) // 2)
        menu.geometry(f"{menu_width}x{menu_height}+{posx}+{posy}")

        menu.resizable(False, False)
        menu.title("Rename Recording")
        menu.config(background=self.bg_color)
        menu.grab_set()

        entry_label: Label = Label(menu, text="New Title: ",
                                   font=(self.TEXT_FONT, 10),
                                   background=self.bg_color)
        entry_label.place(relx=0.23, rely=0.3, anchor="center")

        def validate(P):
            if len(P) == 0:
                return True
            elif len(P) <= 23:
                return True
            else:
                return False 
            
        vcmd = (menu.register(validate), '%P')

        title_entry: Entry = Entry(menu, font=(self.TEXT_FONT, 10),
                                   width=16, validate="all",
                                   validatecommand=vcmd)
        title_entry.place(relx=0.65, rely=0.3, anchor="center")
        title_entry.insert(0, current_name)
        title_entry.focus()

        warning_text: Label = Label(menu, text="",
                                    font=(self.TEXT_FONT, 8),
                                    width=15,
                                    background=self.bg_color,
                                    foreground="red")
        warning_text.place(relx=0.39, rely=0.49, anchor="w")

        def rename_file() -> None:
            ## rename the selected audio recording
            new_name: str = title_entry.get().replace('.wav', '')

            if new_name == current_name.replace('.wav', ''):
                menu.destroy()
            else:
                # stop all audio if current audio is being renamed
                if current_name == self.current_replay:
                    self.playing_audio_paused = False
                    self.pause_button.config(text="Pause")
                    self.current_audio_selection.config(text=self.current_replay)
                    self.current_replay = ""

                time.sleep(0.1)

                # update list
                new_path: str = f"{new_name}.wav"
                if new_path in self.recordings:
                    warning_text.config(text="*file name taken")
                elif new_name == "":
                    warning_text.config(text="*enter a title")
                else:
                    self.recordings.pop(index)
                    self.recordings.insert(index, new_path)

                    # rename file
                    os.rename(f"audio_recordings/{current_name}",
                            f"audio_recordings/{new_path}")
                
                    
                    self.update_recording_listbox()
                    
                    if self.current_replay:
                        # get the index of the current replay and set the selection
                        self.current_audio = self.current_replay
                        idx: int = self.recordings[::-1].index(self.current_replay)
                        self.recording_listbox.select_set(idx)
                        self.current_audio_selection.config(text=self.current_audio)
                    else:
                        # set current audio selection to the renamed audio
                        self.recording_listbox.select_set(index)
                        self.current_audio = f"{new_name}.wav"
                        self.current_audio_selection.config(text=self.current_audio)
                    
                    menu.destroy()


        confirm_rename_button: Button = Button(menu, text="Rename",
                                               font=(self.BUTTON_FONT, 8),
                                               command=rename_file)
        confirm_rename_button.place(relx=0.5, rely=0.7, anchor="center")
        

    def delete_recording(self) -> None:
        """
        Delete the selected audio recording.
        """
        try:
            index: int = self.recording_listbox.curselection()[0]
            current_recording: str = self.recording_listbox.get(index)
        except IndexError:
            return
        
        if self.recording_audio:
            return
    
        if current_recording == self.current_replay:
            # pause the replay
            self.playing_audio = False
            self.playing_audio_paused = True
            self.pause_button.config(text="Resume")
            current: str = self.current_replay
            self.current_audio_selection.config(text=f"{current}(paused)")
            self.root.title("Voice Recorder")
        
        # create and launch a pop-up menu to confim deletion.
        menu: Toplevel = Toplevel()

        root_geometry: str = self.root.wm_geometry(None)

        root_width: int = int(root_geometry.split('x')[0])
        root_height: int = int(root_geometry.split('+')[0].split('x')[1])

        menu_width: int = 260
        menu_height: int = 100

        posx: int = int(root_geometry.split('+')[1]) + \
            ((root_width - menu_width) // 2)
        posy: int = int(root_geometry.split('+')[2]) + \
            ((root_height - menu_height) // 2)
        menu.geometry(f"{menu_width}x{menu_height}+{posx}+{posy}")

        menu.resizable(False, False)
        menu.title("Delete Recording")
        menu.config(background=self.bg_color)
        menu.grab_set()
        
        self.delete_label: Label = Label(menu, font=(self.TEXT_FONT, 10),
                                         text="Delete the following file?"
                                         f"\n>{current_recording}",
                                         background=self.bg_color)
        self.delete_label.place(relx=0.5, rely=0.3, anchor="center")

        def delete() -> None:
            ## delete the selected audio recording
            # stop all audio if current audio is being deleted
            if current_recording == self.current_replay:
                self.playing_audio_paused = False
                self.pause_button.config(text="Pause")
                self.current_replay = ""

            time.sleep(0.1)

            # remove from the recording list
            self.recordings.remove(current_recording)

            # delete the audio file
            os.remove(f"audio_recordings/{current_recording}")

            self.update_recording_listbox()

            if self.current_replay:
                # get the index of the current replay and set the selection
                self.current_audio = self.current_replay
                idx: int = self.recordings[::-1].index(self.current_replay)
                self.recording_listbox.select_set(idx)
                self.current_audio_selection.config(text=self.current_audio)
            else:
                # set current audio to none and update ui
                self.current_audio = ""
                self.current_audio_selection.config(text=self.current_audio)

            menu.destroy()

        def cancel() -> None:
            # cancel deletion and close the pop-up window
            menu.destroy()

        delete_button: Button = Button(menu, text="Delete",
                                     font=(self.BUTTON_FONT, 8),
                                     width=8,
                                     command=delete)
        delete_button.place(relx=0.3, rely=0.7, anchor="center")

        cancel_button: Button = Button(menu, text="Cancel", 
                                     font=(self.BUTTON_FONT, 8),
                                     width=8,
                                     command=cancel)
        cancel_button.place(relx=0.7, rely=0.7, anchor="center")
        

    def delete_all_recordings(self) -> None:
        """
        Delete all audio recordings.
        """
        if self.recording_audio:
            return
        
        if not self.recordings:
            return
        
        # pause the audio
        if self.playing_audio:
            self.playing_audio = False
            self.playing_audio_paused = True
            current: str = self.current_replay
            self.current_audio_selection.config(text=f"{current}(paused)")
            self.pause_button.config(text="Resume")
            self.root.title("Voice Recorder")
        
        # create and launch a pop-up menu to confirm deleteion.
        menu: Toplevel = Toplevel()

        root_geometry: str = self.root.wm_geometry(None)

        root_width: int = int(root_geometry.split('x')[0])
        root_height: int = int(root_geometry.split('+')[0].split('x')[1])

        menu_width: int = 260
        menu_height: int = 100

        posx: int = int(root_geometry.split('+')[1]) + \
            ((root_width - menu_width) // 2)
        posy: int = int(root_geometry.split('+')[2]) + \
            ((root_height - menu_height) // 2)
        menu.geometry(f"{menu_width}x{menu_height}+{posx}+{posy}")

        menu.resizable(False, False)
        menu.title("Delete Recording")
        menu.config(background=self.bg_color)
        menu.grab_set()

        warning_text: Label = Label(menu, text="Are you sure you want to\n"
                                    "delete all recordings?",
                                    font=(self.TEXT_FONT, 10),
                                    justify="center",
                                    foreground="red",
                                    background=self.bg_color)
        warning_text.place(relx=0.5, rely=0.3, anchor="center")

        def delete_all() -> None:
            ## delete all audio recordings
            # stop all audio
            if self.playing_audio_paused:
                self.playing_audio_paused = False
                self.pause_button.config(text="Pause")
                self.current_replay = ""

                time.sleep(0.1)

            # delete all audio files
            for audio_file in self.recordings:
                os.remove(f"audio_recordings/{audio_file}")

            # empty list
            self.recordings = []

            # update ui
            self.update_recording_listbox()

            self.current_audio = ""
            self.current_audio_selection.config(text=self.current_audio)

            menu.destroy()

        def cancel() -> None:
            # cancel the deletion
            menu.destroy()

        delete_button: Button = Button(menu, text="DELETE",
                                       font=(self.BUTTON_FONT, 8),
                                       width=8,
                                       command=delete_all)
        delete_button.place(relx=0.3, rely=0.7, anchor="center")

        cancel_button: Button = Button(menu, text="Cancel",
                                       font=(self.BUTTON_FONT, 8),
                                       width=8,
                                       command=cancel)
        cancel_button.place(relx=0.7, rely=0.7, anchor="center")
        

if __name__ == "__main__":
    # create an instance of the recorder application
    Recorder()