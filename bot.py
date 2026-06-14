from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)

from PIL import (
    Image,
    ImageOps,
    ImageEnhance
)

import os

TOKEN = os.getenv("TOKEN")

user_images = {}

# =========================
# START COMMAND
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📸 Send me 1-8 images.\n"
        "Use /done to create collage.\n"
        "Use /clear to remove uploaded images."
    )

# =========================
# CLEAR COMMAND
# =========================
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    if user_id in user_images:

        for file in user_images[user_id]:

            if os.path.exists(file):
                os.remove(file)

    user_images[user_id] = []

    await update.message.reply_text(
        "🗑 Images cleared."
    )

# =========================
# DONE COMMAND
# =========================
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.from_user.id

    if (
        user_id not in user_images
        or len(user_images[user_id]) == 0
    ):

        await update.message.reply_text(
            "❌ No images uploaded."
        )

        return

    await make_collage(
        update,
        context,
        user_id
    )

# =========================
# HANDLE PHOTOS
# =========================
async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.message.from_user.id

    if user_id not in user_images:
        user_images[user_id] = []

    # max 8 images
    if len(user_images[user_id]) >= 20:

        await update.message.reply_text(
            "⚠️ Maximum 8 images allowed."
        )

        return

    if update.message.photo:

        file_id = update.message.photo[-1].file_id

    else:

        file_id = update.message.document.file_id

    file = await context.bot.get_file(file_id)

    path = (
        f"{user_id}_"
        f"{len(user_images[user_id])}.jpg"
    )

    await file.download_to_drive(path)

    user_images[user_id].append(path)

    await update.message.reply_text(
        f"✅ Image added "
        f"({len(user_images[user_id])}/8)"
    )

# =========================
# MAKE COLLAGE
# =========================
async def make_collage(
    update,
    context,
    user_id
):

    images = [
        Image.open(x).convert("RGB")
        for x in user_images[user_id]
    ]

    target_size = (250, 500)

    processed = []

    # process images
    for img in images:

        # crop properly
        img = ImageOps.fit(
            img,
            target_size,
            Image.Resampling.LANCZOS
        )

        # sharpen
        sharpness = ImageEnhance.Sharpness(img)
        img = sharpness.enhance(1.5)

        # contrast
        contrast = ImageEnhance.Contrast(img)
        img = contrast.enhance(1.1)

        processed.append(img)

    n = len(processed)

    # dynamic layout
    if n == 1:
        cols, rows = 1, 1

    elif n == 2:
        cols, rows = 2, 1

    elif n == 3:
        cols, rows = 3, 1

    elif n == 4:
        cols, rows = 2, 2

    elif n <= 6:
        cols, rows = 3, 2

    else:
        cols, rows = 4, 2

    collage = Image.new(
        "RGB",
        (
            cols * target_size[0],
            rows * target_size[1]
        )
    )

    # paste images directly
    for i, img in enumerate(processed):

        x = (i % cols) * target_size[0]
        y = (i // cols) * target_size[1]

        collage.paste(img, (x, y))

    output = f"{user_id}_collage.jpg"

    collage.save(
        output,
        quality=100,
        subsampling=0
    )

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=open(output, "rb")
    )

    # cleanup
    for file in user_images[user_id]:

        if os.path.exists(file):
            os.remove(file)

    if os.path.exists(output):
        os.remove(output)

    user_images[user_id] = []

# =========================
# APP SETUP
# =========================
app = (
    ApplicationBuilder()
    .token(TOKEN)
    .build()
)

# commands
app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    CommandHandler("done", done)
)

app.add_handler(
    CommandHandler("clear", clear)
)

# image handler
app.add_handler(
    MessageHandler(
        filters.PHOTO | filters.Document.IMAGE,
        handle_photo
    )
)

print("🚀 Bot running...")

app.run_polling()
