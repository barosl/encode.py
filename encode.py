#!/usr/bin/env python

import sys
import os
import re

CFG_FPATH = '~/.encoderc'

try: execfile(os.path.expanduser(CFG_FPATH))
except IOError:
	print >> sys.stderr, '* Configuration file %s not exists' % CFG_FPATH
	sys.exit(1)

def sh_escape(text):
	return '\'%s\'' % text.replace('\'', '\'\\\'\'')

def get_new_size(w, h, max_w, max_h):
	if w > max_w:
		h = h*max_w/w
		w = max_w

	if h > max_h:
		w = w*max_h/h
		h = max_h

	return w, h

def encode(fpath):
	if not os.path.exists(fpath):
		print >> sys.stderr, '* File not exists'
		return False

	fname = os.path.basename(fpath)

	try:
		data = os.popen('mplayer -vo null -ao null -frames 0 -identify %s 2>/dev/null' % sh_escape(fpath)).read()
		ori_w = int(re.search('(?m)^ID_VIDEO_WIDTH=([0-9]+)$', data).group(1))
		ori_h = int(re.search('(?m)^ID_VIDEO_HEIGHT=([0-9]+)$', data).group(1))
		try: a_chs = int(re.search('(?m)^ID_AUDIO_NCH=([0-9]+)$', data).group(1))
		except AttributeError: a_chs = 0
	except AttributeError:
		print >> sys.stderr, '* Unable to obtain enough information from video'
		return False
	new_w, new_h = get_new_size(ori_w, ori_h, cfg['v_w'], cfg['v_h'])

	s_opts = '-nosub'
	if cfg['s_enabled']:
		s_opts = ('''
			-font %s
			-subcp %s
			-subfont-text-scale %d
			-subfont-outline %d
			''' % (
				sh_escape(cfg['s_font']),
				cfg['s_enc'],
				cfg['s_size'],
				cfg['s_outline'],
				))

		if cfg['s_lang']: s_opts += ' -slang %s' % ','.join(cfg['s_lang'])
		if cfg['s_id'] != -1: s_opts += ' -sid %d' % cfg['s_id']

		s_exts = ['smi', 'srt']
		for ext in s_exts:
			found = False
			for ext2 in ext.lower(), ext.upper():
				s_fpath = fpath[:fpath.rindex('.')]+'.'+ext2
				if os.path.exists(s_fpath):
					s_opts += ('''
						-sub %s
						-nosub
						''' % (
							sh_escape(s_fpath),
							))
					found = True
					break
			if found: break

		cfg['use_mencoder'] = True
	s_opts = s_opts.replace('\n', ' ')

	a_opts = ''
	if cfg['a_norm']: a_opts += ' -af-add volnorm'
	if cfg['a_lang']: a_opts += ' -alang %s' % ','.join(cfg['a_lang'])
	if cfg['a_id'] != -1: a_opts += ' -aid %d' % cfg['a_id']

	if a_chs <= 2: pan_opts = ''
	elif a_chs == 6: pan_opts = '-af pan=2:0.5:0:0:0.5:0.33:0:0:0.33:0.5:0.5:0.5:0.5'
	else:
		print >> sys.stderr, '* Downmixing %d channel to stereo is not supported' % a_chs
		return False

	if cfg['use_mencoder']:
		new_fpath = cfg['out_dir']+'/'+fname[:fname.rindex('.')]+'.avi'

		cmd = '''
			mencoder %s -o %s
			-mc 0 -noskip
			-of avi -noodml
			-vf-add scale=%d:%d
			-af-add channels=2

			-demuxer lavf

			%s
			%s
			%s
			''' % (
				sh_escape(fpath), sh_escape(new_fpath),
				new_w, new_h,
				s_opts,
				a_opts,
				pan_opts,
				)

		if False: # Broken: This method does not generate a valid video stream
			cmd = '''
				%s
				-ovc x264 -x264encopts threads=%d:bitrate=%d:global_header:profile=high:preset=medium:tune=animation
				-oac faac -faacopts br=%d:mpeg=4:object=2:raw
				''' % (
					cmd,
					cfg['threads'],
					cfg['v_br'],
					cfg['a_br'],
					)
		elif False: # Broken: And this code does not guarantee a AAC-LC stream
			cmd = '''
				%s
				-ovc lavc -lavcopts threads=%d:vcodec=libx264:vbitrate=%d:o=qcomp=0.6,qmin=10,qmax=51,qdiff=4,coder=1,flags=+loop,cmp=+chroma,partitions=+parti8x8+parti4x4+partp8x8+partb8x8,me_method=umh,subq=8,me_range=16,g=250,keyint_min=25,sc_threshold=40,i_qfactor=0.71,b_strategy=2,bf=3,refs=4,directpred=3,trellis=1,flags2=+wpred+mixed_refs+dct8x8+fastpskip,wpredp=2
				-oac faac -faacopts br=%d:mpeg=4:object=2:raw
				''' % (
					cmd,
					cfg['threads'],
					cfg['v_br'],
					cfg['a_br'],
					)
		else: # So we use MP3 instead
			cmd = '''
				%s
				-ovc lavc -lavcopts threads=%d:vcodec=libx264:vbitrate=%d:o=qcomp=0.6,qmin=10,qmax=51,qdiff=4,coder=1,flags=+loop,cmp=+chroma,partitions=+parti8x8+parti4x4+partp8x8+partb8x8,me_method=umh,subq=8,me_range=16,g=250,keyint_min=25,sc_threshold=40,i_qfactor=0.71,b_strategy=2,bf=3,refs=4,directpred=3,trellis=1,flags2=+wpred+mixed_refs+dct8x8+fastpskip,wpredp=2
				-oac mp3lame -lameopts br=%d
				''' % (
					cmd,
					cfg['threads'],
					cfg['v_br'],
					cfg['a_br'],
					)
	else:
		new_fpath = cfg['out_dir']+'/'+fname[:fname.rindex('.')]+'.mp4'

		cmd = ''
		a_ch_opts = ''

		if a_chs:
			cmd += '''
				mplayer %s -ao pcm:file=/dev/stdout:fast
				-really-quiet
				-novideo -vc null -vo null
				-af-add channels=2

				-demuxer lavf

				%s
				%s

				|
				''' % (
					sh_escape(fpath),
					a_opts,
					pan_opts,
					)

			a_ch_opts = '-i -'

		cmd += '''
			ffmpeg -y -threads %d -i %s %s -vcodec libx264 -vpre hq -s %dx%d -b %dk -acodec libfaac -ab %dk -ac 2 %s
			''' % (
				cfg['threads'],
				sh_escape(fpath),
				a_ch_opts,
				new_w, new_h,
				cfg['v_br'],
				cfg['a_br'],
				sh_escape(new_fpath),
				)

	if cfg['debug']: print >> sys.stderr, '** Command before processing begins\n%s\n** Command before processing ends' % cmd

	cmd = cmd.replace('\n', ' ')
	cmd = 'nice -n10 sh -c %s' % sh_escape(cmd)

	if cfg['debug']: print >> sys.stderr, '** Command after processing begins\n%s\n** Command after processing ends' % cmd

	if os.system(cmd):
		if not cfg['keep_unfinished']:
			try: os.remove(new_fpath)
			except OSError: pass

		print >> sys.stderr, '* Program returned an error'
		return False

	return True

def main():
	if len(sys.argv) < 2:
		print >> sys.stderr, '* Nothing to do'
		sys.exit(0)

	for fpath in sys.argv[1:]:
		if not encode(fpath):
			print >> sys.stderr, '* Failed to encode %s' % os.path.basename(fpath)
			sys.exit(2)

if __name__ == '__main__':
	main()
