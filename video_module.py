from engine import SystemState
from engine import Utilities
from engine import Menu
from engine import Screen
from engine import TextWriter
from engine import Events
import RPi.GPIO
import pyaudio
import wave
import atexit
import io
import stat
import os
import signal
import picamera
import time
import sys
import threading
import Queue

signal.signal(signal.SIGINT, Utilities.GracefulExit)

class VideoState(object):
  pass

def Init():
  # System Setup
  RPi.GPIO.setup(7, RPi.GPIO.OUT) #Flash RPi.GPIO
  RPi.GPIO.setup(8, RPi.GPIO.IN, pull_up_down=RPi.GPIO.PUD_UP) #Button RPi.GPIO
  RPi.GPIO.output(7, False)
  SystemState.camera.image_effect = 'none'
  
  # Iterating Variable Setup
  SystemState.VideoState = VideoState
  SystemState.VideoState.setting = 'none'
  SystemState.VideoState.image_effect = 0
  SystemState.VideoState.iso = 0
  SystemState.VideoState.rotation = 0
  SystemState.VideoState.brightness = 5
  SystemState.VideoState.saturation = 10
  SystemState.VideoState.contrast = 10
  SystemState.VideoState.sharpness = 10
  SystemState.VideoState.zoom = 0
  SystemState.VideoState.meter_mode = 0
  SystemState.VideoState.awb_mode = 0
  SystemState.VideoState.exposure_mode = 0
  SystemState.VideoState.video_stabilization = 0
 
  # Video Associated Variable Setup
  SystemState.VideoState.current_video = None
  SystemState.VideoState.video_filename = None
  SystemState.VideoState.video_archive = None
  SystemState.VideoState.video_tally = None
  SystemState.VideoState.video_count = 0
  SystemState.VideoState.video_stream = True
  SystemState.VideoState.video_duration = 0
  SystemState.VideoState.video_recording = False
  SystemState.VideoState.playback_state = 'pause'
  SystemState.VideoState.video_path = 'media/video/'
  SystemState.VideoState.video_preview_path = SystemState.VideoState.video_path + '.preview/'
  SystemState.VideoState.audio_message_queue = Queue.Queue()
  SystemState.VideoState.video_message_queue = Queue.Queue()
  
  # Lists of camera effects
  SystemState.VideoState.iso_values = [0, 100, 200, 320, 400, 500, 640, 800]
  SystemState.VideoState.image_effect_values = [
      'none', 'negative', 'solarize', 'sketch', 'denoise', 'emboss', 'oilpaint',
      'hatch','gpen', 'pastel', 'watercolor', 'film', 'blur', 'saturation', 
      'colorswap', 'washedout', 'posterise',  'colorpoint', 'colorbalance', 
      'cartoon', 'deinterlace1', 'deinterlace2'
  ]
  SystemState.VideoState.awb_mode_values = [
      'auto', 'sunlight', 'cloudy', 'shade', 'tungsten', 'fluorescent',
      'incandescent', 'flash', 'horizon', 'off'
  ]
  SystemState.VideoState.rotation_values = [0, 90, 180, 270]
  SystemState.VideoState.brightness_values = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
  hundred_container = [-100, -90, -80, -70, -60, -50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
  SystemState.VideoState.saturation_values = hundred_container 
  SystemState.VideoState.contrast_values = hundred_container
  SystemState.VideoState.sharpness_values = hundred_container
  
  SystemState.VideoState.zoom_values = [
      (0.0, 0.0, 1.0, 1.0),
      (0.1, 0.1, 0.9, 0.9),
      (0.225, 0.225, 0.8, 0.8),
      (0.25, 0.25, 0.7, 0.7),
      (0.275, 0.275, 0.6, 0.6),
      (0.3, 0.3, 0.5, 0.5),
      (0.325, 0.325, 0.4, 0.4),
      (0.35, 0.25, 0.3, 0.3),
      (0.375, 0.375, 0.2, 0.2),
      (0.4, 0.4, 0.1, 0.1),
  ]
  SystemState.VideoState.meter_mode_values = [
      'average', 'spot', 'backlit', 'matrix'
  ]
  SystemState.VideoState.exposure_mode_values = [
      'auto', 'night', 'nightpreview', 'backlight', 'spotlight',
      'sports', 'snow', 'beach', 'verylong', 'fixedfps', 'antishake',
      'fireworks', 'off'
  ]
  SystemState.VideoState.video_stabilization_values = [False, True]

  __MakeVideoPath()
  return SystemState 


def __PreviousSetting(property_list, property_name):
  """Moves to the previous setting in the menu."""
  properties = getattr(SystemState.VideoState, property_list)
  index = getattr(SystemState.VideoState, property_name)
  if index > 0: 
    index -= 1
  else:
    index = len(properties) - 1
  __ProcessSettingsValues(property_name, properties, index)
  
def __NextSetting(property_list, property_name):
  """Moves to the next settng in the menu."""
  properties = getattr(SystemState.VideoState, property_list)
  index = getattr(SystemState.VideoState, property_name)
  if index < len(properties) - 1: 
    index += 1
  else:
    index = 0
  __ProcessSettingsValues(property_name, properties, index)
  
def __CurrentSetting(property_list, property_name):
  """Display's items on screen when you first enter a menu."""
  properties = getattr(SystemState.VideoState, property_list)
  index = getattr(SystemState.VideoState, property_name)
  __ProcessSettingsValues(property_name, properties, index)


def __ProcessSettingsValues(property_name, properties, index):
  """Fetches values and prints them on screen for Next and Previous. """
  property_value = properties[index]

  # Setting values in SystemState.camera from SystemState.VideoState.
  setattr(SystemState.camera, property_name, property_value)
  setattr(SystemState.VideoState, property_name, index)
  property_type = type(property_value)
  
  # Ensures default 'auto' values are printed on screen.
  if property_value == 0 and property_type is not bool:
    property_value = 'Auto'
  
  # Makes 'zoom' human readable.
  if property_type is tuple: 
    if index == 0:
      index = None
    property_value = str(index) 
  
  # Removing underscores and writing values to the screen.
  property_name = ' '.join(property_name.split('_'))
  __WriteSettingsTitle(property_name)
  __WriteSettingsValue(property_value)


def __WriteSettingsValue(text):
  """Writes settings values for each menu item."""
  TextWriter.Write(
    state=SystemState, 
    text=str(text).title(), 
    position=(160, 110), 
    centered=True,
    size=20,
    permatext=True,
    color=(57, 255, 20)
  )

  
def __WriteSettingsTitle(text):
  """Writes title values for each menu item."""
  TextWriter.Write(
    state=SystemState, 
    text=str(text).title(), 
    position=(160, 10), 
    centered=True,
    size=25,
    permatext=True,
    color=(57, 255, 20)
  )


def Process():
  """Processing button presses."""
  button = str(SystemState.pressed_button)
  pygame = SystemState.pygame
  screen = SystemState.screen
  screen_mode = SystemState.screen_mode
  
  if button == 'library':
    OpenAlbum()
    Menu.JumpTo(screen_mode=4)
  elif button == 'go_back':
    Menu.Back()
    SystemState.VideoState.setting = 'none'
  elif button == 'play':
    __PlayVideo()
  elif button == 'settings':
    Menu.JumpTo(screen_mode=2, refresh_screen=False)
  elif button == 'delete':
    if SystemState.VideoState.video_count > 0:
      Menu.JumpTo(screen_mode=5)
      TextWriter.Write(
          state=SystemState, 
          text='Delete?', 
          position=(125, 75), 
          size=20
      )
  elif button == 'right_arrow':
    __ProcessRightArrow()
  elif button == 'left_arrow':
    __ProcessLeftArrow()
  elif button == 'iso':
    Menu.JumpTo(screen_mode=3)
    SystemState.VideoState.setting = 'iso'
  elif button == 'image_effect':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'image_effect'
  elif button == 'rotation':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'rotation'
  elif button == 'brightness':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'brightness'
  elif button == 'saturation':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'saturation'
  elif button == 'contrast':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'contrast'
  elif button == 'sharpness':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'sharpness'
  elif button == 'zoom':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'zoom'
  elif button == 'meter_mode':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'meter_mode'
  elif button == 'awb':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'awb_mode'
  elif button == 'video_stabilization':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'video_stabilization'
  elif button == 'exposure_mode':
    Menu.JumpTo(screen_mode=3, refresh_screen=False)
    SystemState.VideoState.setting = 'exposure_mode'
  elif button == 'accept':
    __DeleteVideo()
    Menu.Back()
    OpenAlbum()
  elif button == 'decline':
    Menu.Back()
    OpenAlbum()
  
  # Displaying settings title and values when you first enter a menu.
  if SystemState.screen_mode == 2 and SystemState.next_screen_mode == 3:
    setting = SystemState.VideoState.setting
    setting_values = setting + '_values'
    __CurrentSetting(setting_values, setting)
 
def __ProcessLeftArrow():
  """Processing left arrow input for each menu item."""
  if SystemState.VideoState.setting == 'image_effect':
    __PreviousSetting('image_effect_values', 'image_effect')
  elif SystemState.VideoState.setting == 'iso':
    __PreviousSetting('iso_values', 'iso')
  elif SystemState.VideoState.setting == 'rotation':
    __PreviousSetting('rotation_values', 'rotation')
  elif SystemState.VideoState.setting == 'brightness':
    __PreviousSetting('brightness_values', 'brightness')
  elif SystemState.VideoState.setting == 'saturation':
    __PreviousSetting('saturation_values', 'saturation')
  elif SystemState.VideoState.setting == 'contrast':
    __PreviousSetting('contrast_values', 'contrast')
  elif SystemState.VideoState.setting == 'sharpness':
    __PreviousSetting('sharpness_values', 'sharpness')
  elif SystemState.VideoState.setting == 'zoom':
    __PreviousSetting('zoom_values', 'zoom')
  elif SystemState.VideoState.setting == 'meter_mode':
    __PreviousSetting('meter_mode_values', 'meter_mode')
  elif SystemState.VideoState.setting == 'awb_mode':
    __PreviousSetting('awb_mode_values', 'awb_mode')
  elif SystemState.VideoState.setting == 'video_stabilization':
    __PreviousSetting('video_stabilization_values', 'video_stabilization')
  elif SystemState.VideoState.setting == 'exposure_mode':
    __PreviousSetting('exposure_mode_values', 'exposure_mode')
  elif SystemState.screen_mode == 4:
    if SystemState.VideoState.video_count > 0:
      __PreviousVideo()

def __ProcessRightArrow():
  """Processing right arrow input for each menu item."""
  if SystemState.VideoState.setting == 'image_effect':
    __NextSetting('image_effect_values', 'image_effect')
  elif SystemState.VideoState.setting == 'iso':
    __NextSetting('iso_values', 'iso')
  elif SystemState.VideoState.setting == 'rotation':
    __NextSetting('rotation_values', 'rotation')
  elif SystemState.VideoState.setting == 'brightness':
    __NextSetting('brightness_values', 'brightness')
  elif SystemState.VideoState.setting == 'saturation':
    __NextSetting('saturation_values', 'saturation')
  elif SystemState.VideoState.setting == 'contrast':
    __NextSetting('contrast_values', 'contrast')
  elif SystemState.VideoState.setting == 'sharpness':
    __NextSetting('sharpness_values', 'sharpness')
  elif SystemState.VideoState.setting == 'zoom':
    __NextSetting('zoom_values', 'zoom')
  elif SystemState.VideoState.setting == 'meter_mode':
    __NextSetting('meter_mode_values', 'meter_mode')
  elif SystemState.VideoState.setting == 'awb_mode':
    __NextSetting('awb_mode_values', 'awb_mode')
  elif SystemState.VideoState.setting == 'video_stabilization':
    __NextSetting('video_stabilization_values', 'video_stabilization')
  elif SystemState.VideoState.setting == 'exposure_mode':
    __NextSetting('exposure_mode_values', 'exposure_mode')
  elif SystemState.screen_mode == 4:
    if SystemState.VideoState.video_count > 0:
      __NextVideo()
   
def __MakeVideoPath():
  """Creates a folder that holds videos."""
  if os.path.exists(SystemState.VideoState.video_preview_path) == False:
    os.makedirs(SystemState.VideoState.video_preview_path)
  os.chown(SystemState.VideoState.video_preview_path, SystemState.uid, SystemState.gid)

def __CallRecordAudio(timestamp):
  """Calls the _RecordAudio function in a thread."""
  args = (timestamp)
  thread = threading.Thread(target=__RecordAudio, args=(timestamp,))
  thread.setDaemon(True)
  thread.start()

def __CallRecordVideo(timestamp):
  """Calls the __RecordVideo function in a thread."""
  args = (timestamp)
  thread = threading.Thread(target=__RecordVideo, args=(timestamp,))
  thread.setDaemon(True)
  thread.start()

def __CallConvertVideo(timestamp):
  """Calls the __ConvertVideo function in a thread."""
  args = (timestamp)
  thread = threading.Thread(target=__ConvertVideo, args=(timestamp,))
  thread.setDaemon(True)
  thread.start()

def __RecordAudio(timestamp):
  """Setting up variables for camera."""
  CHUNK = 8192
  FORMAT = pyaudio.paInt16
  CHANNELS = 1
  RATE = int(SystemState.pyaudio.get_device_info_by_index(0)['defaultSampleRate'])
  FILENAME = SystemState.VideoState.video_path + timestamp + '.wav'
  RECORD_SECONDS = 10800
  frames = []

  # Clearing the queue messages just in case.
  with SystemState.VideoState.audio_message_queue.mutex:
    SystemState.VideoState.audio_message_queue.queue.clear() 

  # Setting up stream for audio.
  stream = SystemState.pyaudio.open(
      format=FORMAT,
      channels=CHANNELS,
      rate=RATE,
      input=True,
      output=True,
      frames_per_buffer=CHUNK
  )

  # Recording data to a wave file.
  for i in range(0, int(RATE/CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)
    # Try placing the information inside the audio message queue.
    try:
      audio_message_queue = SystemState.VideoState.audio_message_queue.get(False)
    # If the queue is already empty, set it to none.
    except Queue.Empty:
      audio_message_queue = None
    
    #If there is something inside the queue, read it.
    if audio_message_queue != None:
      if audio_message_queue.get('recording') == False:
        break

  # Stopping and closing stream.
  stream.stop_stream()
  stream.close()

  # Converting stream data into a wave file.
  wavefile = wave.open(FILENAME, 'wb')
  wavefile.setnchannels(CHANNELS)
  wavefile.setsampwidth(SystemState.pyaudio.get_sample_size(FORMAT))
  wavefile.setframerate(RATE)
  wavefile.writeframes(b''.join(frames))
  wavefile.close()

def __StopRecordingAudio():
  """Setting up all the variables to stop recording audio."""
  SystemState.VideoState.recording_audio = False
  audio_action = {'recording': False}
  video_action = {'recording': False}
  SystemState.VideoState.video_message_queue.put(video_action)
  SystemState.VideoState.audio_message_queue.put(audio_action)
  

def __RecordVideo(timestamp):
  """Records video files."""
  video_path = SystemState.VideoState.video_path
  video_preview_path = SystemState.VideoState.video_preview_path
  
  # Setting up paths for videos.
  h264_filepath = video_path + timestamp
  mjpeg_filepath = video_preview_path + timestamp

  # Start recording a high res (.h264) and low res (.mjpeg).
  SystemState.camera.start_recording(h264_filepath + '.h264', splitter_port=2, resize=(1920, 1080))
  SystemState.camera.start_recording(mjpeg_filepath + '.mjpeg', splitter_port=3, resize=(320, 240))

  # Wait until the red button is released.
  RPi.GPIO.wait_for_edge(8, RPi.GPIO.RISING)

  # Stop recording the high res and low res video_archive.
  __StopRecordingAudio()
  SystemState.camera.stop_recording(splitter_port=2)
  SystemState.camera.stop_recording(splitter_port=3)

  # Call threading function to convert a video.
  __CallConvertVideo(timestamp)

def __ConvertVideo(timestamp):
  """Convert's second mpjpeg video to mpeg which pygame can play."""
  # Setting up local varables.
  video_path = SystemState.VideoState.video_path
  video_preview_path = SystemState.VideoState.video_preview_path
  mjpeg_filepath = video_preview_path + timestamp + '.mjpeg'  
  mpeg_filepath = video_preview_path + timestamp + '.mpeg'  
  wav_filepath = video_path + timestamp + '.wav'
  process_filepath = mjpeg_filepath + '.process'
  mode = 0600|stat.S_IRUSR
  time.sleep(1) 

  # Converting video files to make preview files. 
  os.mknod(process_filepath, mode)
  ffmpeg_a = 'ffmpeg -i ' + mjpeg_filepath + " -target ntsc-vcd "  
  ffmpeg_b = ' -vcodec mpeg1video -an ' +  mpeg_filepath + ' -threads 0'
  ffmpeg_convert = ffmpeg_a + ffmpeg_b

  # Executing the ffmpeg command and removing the process files.
  os.system(ffmpeg_convert)
  os.remove(mjpeg_filepath) 
  os.remove(process_filepath)

def OpenAlbum():

  """Opens the contents inside of the videos folder."""
  # Setup the preview path as the path for the video count.
  path = SystemState.VideoState.video_preview_path 
  SystemState.VideoState.video_archive = os.listdir(path)
  SystemState.VideoState.video_archive = [os.path.join(path, pic) for pic in SystemState.VideoState.video_archive]
  SystemState.VideoState.video_archive = sorted(SystemState.VideoState.video_archive)
  SystemState.VideoState.video_count = len(SystemState.VideoState.video_archive) 
  processing_videos = []
  
  # If there's a video in the directory, set it as current video.
  if SystemState.VideoState.video_count > 0:
    if SystemState.VideoState.current_video in SystemState.VideoState.video_archive:
      SystemState.VideoState.video_index = SystemState.VideoState.video_archive.index(SystemState.VideoState.current_video)
    else:
      SystemState.VideoState.video_index = SystemState.VideoState.video_count - 1
      SystemState.VideoState.current_video = SystemState.VideoState.video_archive[SystemState.VideoState.video_index]
    __ShowVideo(SystemState.VideoState.current_video)
  # If there are no videos, just write "no videos".
  else:
    TextWriter.Write(
        state=SystemState,
        text='No Videos',
        position=(110, 100),
        centred=True,
        size=20,
        permatext=True
    )

def __ShowVideo(filename):
  """Shows a picture of the video file."""
  pygame = SystemState.pygame
  screen = SystemState.screen
  
  # Setting up movie for pygame 
  SystemState.VideoState.movie = pygame.movie.Movie(filename)
  SystemState.VideoState.movie.render_frame(1)
  if SystemState.VideoState.video_archive != None and SystemState.screen_mode == 3:
    # Remove 'PREVIEW-' and path leaving just unix time.
    utime_string = os.path.basename(filename).split('-')[-1].split('.')[0]
    timestamp = time.ctime(int(utime_string))

    # Writing the time and position of the photo on the screen.
    TextWriter.Write(
        state=SystemState, 
        text=timestamp, 
        position=(90, 10), 
        size=12
    )
  
def __PlayVideo():
  """Plays the video file (preview) on the camera's screen."""
  # If there's more than one video, go ahead and play the video we're on.
  if SystemState.VideoState.video_count > 0:
    pygame = SystemState.pygame 
    modes = pygame.display.list_modes(16)
    movie_screen = pygame.display.set_mode(modes[0], pygame.FULLSCREEN, 16)
    SystemState.VideoState.movie.set_display(movie_screen)
    SystemState.VideoState.movie.play()
    SystemState.VideoState.movie_duration = SystemState.VideoState.movie.get_length()
    time.sleep(SystemState.VideoState.movie_duration + .02)
    OpenAlbum()
  

def __NextVideo():
  """Moves to the next video in the library."""
  # If the video is not at the end of the list, go to the next one.
  if SystemState.VideoState.video_index < SystemState.VideoState.video_count - 1:
    SystemState.VideoState.video_index += 1
  # If the video is at the end of the list, send it back to the first one.
  else:
    SystemState.VideoState.video_index = 0
  filename = SystemState.VideoState.video_archive[SystemState.VideoState.video_index]
  SystemState.VideoState.video_tally = str(SystemState.VideoState.video_index + 1) + '/' + str(SystemState.VideoState.video_count)
  __ShowVideo(filename)
  

def __PreviousVideo():
  """Moves to the previous video in the library."""
  # If the video more than the first one, then move backwards through the list.
  if SystemState.VideoState.video_index > 0:
    SystemState.VideoState.video_index -= 1
  # If the video is the last one, then go back to the beginning.
  else:
    SystemState.VideoState.video_index = SystemState.VideoState.video_count - 1
  filename = SystemState.VideoState.video_archive[SystemState.VideoState.video_index]
  SystemState.VideoState.video_tally = str(SystemState.VideoState.video_index + 1) + '/' + str(SystemState.VideoState.video_count)
  __ShowVideo(filename)
  

def __DeleteVideo():
  """Delete a video."""
  preview_video = SystemState.VideoState.current_video
  
  # Setting up files to be deleted. 
  full_video = preview_video.split('/.preview')
  full_video = full_video[0] + full_video[1]
  full_video = full_video.split('.')
  full_video = full_video[0] + '.h264'
  
  # Attempting to delete the files above.
  try:
    os.remove(preview_video)
  except: # TODO:print that preview couldn't be removed.
    print "Couldn't remove preview image" 
  
  try:
    SystemState.VideoState.video_archive.remove(preview_video)
  except: # TODO: print that file was not removed from library.
    print "Couldn't remove from library"
  
  try:
    os.remove(full_video)
  except: # TODO: print that image not removed.
    print "Image not removed"
    
   
def Main():
  """Main loop for the camera application."""
  pygame = SystemState.pygame
  SystemState.camera.resolution = (320, 240)
  
  while SystemState.application == 'video':
    # Check for button presses, messages, and which mode we're in.
    Events.CheckEvents()
    if SystemState.screen_mode in (1, 2, 3):
      SystemState.VideoState.video_stream = True
    else:
      SystemState.VideoState.video_stream = False
    try:
      video_message_queue = SystemState.VideoState.video_message_queue.get(None)
    except Queue.Empty:
      video_message_queue = None
    
    # Checking video message queue for record messages.
    if video_message_queue != None:
      recording_state = video_message_queue.get('recording')
      if recording_state == True:
        timestamp = str(int(time.time()))
        __CallRecordAudio(timestamp)
        __CallRecordVideo(timestamp)
        SystemState.VideoState.video_recording = True
      elif recording_state == False:
        SystemState.VideoState.video_recording = False
        TextWriter.ClearPermatext()
    
    # Checking the gpio button that starts recording.
    if SystemState.VideoState.video_recording == False:
      if not RPi.GPIO.input(8) and SystemState.screen_mode == 1:
        SystemState.VideoState.video_message_queue.put({'recording': True})
        Menu.JumpTo(screen_mode=6)
        TextWriter.Write(
          text='Rec', 
          position=(10, 10), 
          color=(255,0,0), 
          permatext=True,
          state=SystemState, 
          size=20
        ) 
    
    # Check if we are in a streaming mode. If so, throw frames at the screen.
    if SystemState.VideoState.video_stream == True:
      SystemState.VideoState.stream = io.BytesIO() # Capture into in-memory stream
      SystemState.camera.capture(SystemState.VideoState.stream, use_video_port=True, splitter_port=0, format='rgb')
      SystemState.VideoState.stream.seek(0)
      SystemState.VideoState.stream.readinto(SystemState.rgb)  
      SystemState.VideoState.stream.close()
      SystemState.VideoState.img = SystemState.pygame.image.frombuffer(SystemState.rgb[0: (320 * 240 * 3)], (320, 240), 'RGB' )
      xa = (320 - SystemState.VideoState.img.get_width() ) / 2
      ya = (240 - SystemState.VideoState.img.get_height()) / 2
      Screen.RefreshScreen(image=SystemState.VideoState.img, wx=xa, wy=ya)
