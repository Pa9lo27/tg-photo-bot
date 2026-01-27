from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image
import openai
import os

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/process")
async def process_image(
    file: UploadFile,
    action: str = Form(...),
    size: int = Form(None)
):
    image = Image.open(file.file).convert("RGB")
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    buffered.seek(0)

    prompt = "Покращити це фото, зробити чітким, без пікселів"
    if action == "expand" and size:
        prompt += f", та змінити розмір до {size}x{size}"

    response = openai.images.edit(
        image=buffered,
        prompt=prompt,
        size="1024x1024"
    )

    import base64
    img_data = base64.b64decode(response['data'][0]['b64_json'])
    result_image = BytesIO(img_data)
    result_image.seek(0)

    return StreamingResponse(result_image, media_type="image/png")