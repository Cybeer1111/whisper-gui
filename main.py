import gradio as gr
import whisperx
import subprocess, os, gc
import soundfile as sf
# import torch

def save_audio_to_mp3(audio_tuple, save_path='audios/audio.mp3'):
	rate, y = audio_tuple
	if len(y.shape) == 2:
		y = y.T[0]  # If stereo, take one channel

	# Save as WAV file first
	wav_path = 'audios/temp_audio.wav'
	sf.write(wav_path, y, rate)

	# Convert WAV to MP3 using ffmpeg
	subprocess.run(['ffmpeg', '-i', wav_path, save_path])

	# Remove the temporary WAV file
	os.remove(wav_path)

	return save_path

def transcribe_audio(audio_tuple, device, batch_size, compute_type, language, chunk_size):
	# save copy of audio
	audio_path = save_audio_to_mp3(audio_tuple)

	# Transcription
	print('Loading model...')
	model = whisperx.load_model('large-v2', device, compute_type=compute_type, download_root='models')
	print('Loading audio...')
	audio = whisperx.load_audio(audio_path)
	print('Transcribing...')
	result = model.transcribe(audio, batch_size=batch_size, language=language, chunk_size=chunk_size, print_progress=True)

	# Alignment
	print('Loading alignment model...')
	model_a, metadata = whisperx.load_align_model(language_code=result['language'], device=device, model_dir='models/alignment')
	print('Aligning...')
	aligned_result = whisperx.align(result['segments'], model_a, metadata, audio, device, return_char_alignments=False)
	print('Done!')
	# del model, audio, result, model_a, metadata
	# gc.collect()
	# torch.cuda.empty_cache()
	return ' '.join([segment['text'] for segment in aligned_result['segments']])

def main():
	# Create Gradio Interface
	iface = gr.Interface(
		transcribe_audio,
		[gr.Audio(source='upload', label='Upload Audio File'),
		gr.Radio(['cuda', 'cpu'], value = 'cuda', label='Device'),
		gr.Slider(1, 16, value = 1, label='Batch Size', info='Larger batch sizes may be faster but require more memory'),
		gr.Radio(['int8', 'float16', 'float32'], value = 'int8', label='Compute Type', info='int8 is fastest and requires less memory. float32 is more accurate (The model or your device may not support some data types)'),
		gr.Dropdown(['auto', 'en', 'es', 'fr', 'de', 'it', 'ja', 'zh', 'nl', 'uk', 'pt'], value = 'auto', label='Language', info='Select the language of the audio file. Select "auto" to automatically detect it.'),
		gr.Slider(1, 30, value = 20, label='Chunk Size', info='Larger chunk sizes may be faster but require more memory')],
		gr.outputs.Textbox(label='Transcription'),
		allow_flagging=False,
	)

	# Launch the interface
	iface.launch()

if __name__ == '__main__':
	main()
