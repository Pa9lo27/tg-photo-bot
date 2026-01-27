import redis
import os
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image
import openai
import base64

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379))
)

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

    prompt = "Покращити фото"
    if action == "expand" and size:
        prompt += f" та змінити розмір до {size}x{size}"

    response = openai.images.edit(
        image=buffered,
        prompt=prompt,
        size="1024x1024"
    )

    img_data = base64.b64decode(response['data'][0]['b64_json'])
    result_image = BytesIO(img_data)
    result_image.seek(0)

    r.publish("photo_channel", f"Фото готово для action={action}")

    return StreamingResponse(result_image, media_type="image/png")