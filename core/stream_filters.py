from pytube import YouTube
from pytube.query import StreamQuery

class Stream_Filter:
    def __init__(self, streams):
        """
        stream must be a type of pytube.query.StreamQuery or pytube.YouTube
        """
        if type(streams) == YouTube:
            self.streams = streams.streams
        if type(streams) == StreamQuery:
            self.streams = streams
    
    def get_highest_quality_progressive_stream(self):
        stream = self.streams.filter(progressive=True).order_by("resolution").last()
        return stream

    def get_lowest_quality_progressive_stream(self):
        stream = self.streams.filter(progressive=True).order_by("resolution").first()
        return stream

    def get_highest_quality_video_stream(self):
        stream = self.streams.filter(only_video=True).order_by("resolution").last()
        return stream

    def get_lowest_quality_video_stream(self):
        stream = self.streams.filter(only_video=True).order_by("resolution").first()
        return stream

    def get_highest_quality_audio_stream(self):
        stream = self.streams.filter(only_audio=True).order_by("abr").last()
        return stream

    def get_lowest_quality_audio_stream(self):
        stream = self.streams.filter(only_audio=True).order_by("abr").first()
        return stream
