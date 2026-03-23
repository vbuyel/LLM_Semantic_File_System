import gradio as gr
import requests
from pathlib import Path
import os
import shutil

# def get_response(text: str, file_path: str | None = None) -> str:
def get_response(text: str, file_obj) -> str:
    file_path = None
    if file_obj is not None:
        target_dir = Path("temp_files")
        target_dir.mkdir(exist_ok=True)
        
        filename = getattr(file_obj, "orig_name", None) or os.path.basename(file_obj.name)
        file_path = target_dir / filename
        shutil.copy(file_obj.name, file_path)

        file_path = str(file_path)

    params = {"text": text, "file_path": file_path}
    response = requests.post(
        "http://127.0.0.1:8000/get_response",
        json=params,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()['text']

demo = gr.Interface(
    fn=get_response,
    inputs=[
        gr.Textbox(label="User text"),
        gr.File(),
    ],
    outputs=gr.Textbox(label="Model response"),
)

if __name__ == "__main__":
    demo.launch()
