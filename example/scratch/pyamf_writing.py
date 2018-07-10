import pyamf
import pyamf.amf0

# Initialise empty buffer.
temp_buffer = pyamf.util.BufferedByteStream('')
amf0_encoder = pyamf.amf0.Encoder(temp_buffer)

amf0_encoder.writeElement('onMetaData')
meta_data = {"duration": 0.0, "videocodecid": 2}
amf0_encoder.writeElement(meta_data)

write_buffer = temp_buffer.getvalue()
print([write_buffer])
