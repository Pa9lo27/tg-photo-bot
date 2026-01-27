from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import FileResponse
from PIL import Image
import io

app = FastAPI()

@app.post("/process")
async def process_image(
    file: UploadFile,
    action: str = Form(...),
    size: int = Form(None)
):
    # Читаємо фото
    image = Image.open(file.file)

    # Тестова обробка
    if action == "enhance":
        # Просто робимо апскейл 2x
        image = image.resize((image.width*2, image.height*2))
    elif action == "expand" and size:
        # Робимо апскейл до заданого розміру
        image = image.resize((size, size))

    # Зберігаємо у тимчасовий файл
    output_path = f"temp_output.jpg"
    image.save(output_path)
    return FileResponse(output_path, media_type="image/jpeg")
