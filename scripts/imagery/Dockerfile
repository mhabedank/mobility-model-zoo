# Image generation for the zoo website (feature 016) on the DGX Spark (arm64, CUDA 13).
# The NGC PyTorch container brings torch for the GB10; diffusers comes on top. Its bundled torchao
# is older than diffusers expects and is only an optional import, so it is removed.
FROM nvcr.io/nvidia/pytorch:25.09-py3
RUN pip uninstall -y torchao \
 && pip install --no-cache-dir "diffusers>=0.41" "transformers>=4.46" accelerate sentencepiece protobuf pyyaml "huggingface_hub>=0.30"
WORKDIR /work
