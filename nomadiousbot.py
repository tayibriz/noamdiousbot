import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler , ConversationHandler, callbackcontext
from telegram.ext.filters import Filters 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import mysql.connector
import openai
import requests
import os
from io import BytesIO
from PIL import Image

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
#database config
DB_CONFIG = {
    'user': 'root',
    'password': 'Hellobrother@123',
    'host': 'localhost',
    'database': 'nomad',
}
if not os.path.exists('images'):
    os.makedirs('images')

#initialization
ADMIN_USER_IDS = [5998589745]
ENTER_RESTAURANT_NAME, ENTER_REVIEW = range(2) 
ENTER_RESTAURANT=1
SELECT_COLLAB_OPTION, ENTER_CONTACT = range(2)



#gpt key
openai.api_key = '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'

# Define your bot token
TOKEN = "6306599375:AAEOYwUR4ubBKC_kRbRqTaLhp-SFuc84X_Y"


# Command handler for /start command
from telegram import ReplyKeyboardMarkup, KeyboardButton

def start(update, context):
    user = update.effective_user

    if user is None:
        update.message.reply_text("Hi there! I can only interact with users, not groups or channels.")
        return
    first_name = user.first_name
    update.message.reply_text(f"Hello {first_name}! I'm your friendly Nomadiouskid bot 🍔🍕🍰")

    # Define the keyboard layout
    keyboard = [
        [KeyboardButton("📸 Food Images")],
        [KeyboardButton("📸 Food Reels")],
        [KeyboardButton("🍰 Recipes")],
        [KeyboardButton("reviews")],
        [KeyboardButton("🤝 Want to Collaborate")],
    ]

    # Create a ReplyKeyboardMarkup with the defined keyboard layout
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    update.message.reply_text("What would you like to explore?", reply_markup=reply_markup)

#collaborations function logic

COLLAB_OPTIONS = {
    "1": "1 reel + 1 story",
    "2": "3 reels + 3 story",
    "3": "6 reels + multiple stories",
    "4": "multiple reels + stories",
}

def start_collaboration(update, context):
    user = update.effective_user
    print("User:", user)

    # Send the collaboration options to the user
    keyboard = get_collab_options_markup()
    context.bot.send_message(chat_id=user.id, text="Please choose a collaboration option:", reply_markup=keyboard)

    return SELECT_COLLAB_OPTION

# Define your conversation states here
def get_collab_options_markup():
    keyboard = [
        [InlineKeyboardButton(text, callback_data=key) for key, text in COLLAB_OPTIONS.items()],
        [InlineKeyboardButton("Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)
def select_collab_option(update, context):
    print("select_collab_option function is called")
    query = update.callback_query
    query_data = query.data

    if query_data == "back":
        context.bot.send_message(chat_id=query.message.chat.id, text="You have returned to the main menu.", reply_markup=get_collab_options_markup())
        return SELECT_COLLAB_OPTION
    else:
        context.user_data["collab_option"] = COLLAB_OPTIONS.get(query_data)
        context.bot.send_message(chat_id=query.message.chat.id, text=f"You selected: {context.user_data['collab_option']}\nPlease provide your contact number:")
        return ENTER_CONTACT
    
def save_contact_info(update, context):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    contact_number = update.message.text

    collab_option = context.user_data.get("collab_option")

    if collab_option:
        # Save the contact information and collaboration option to your database
        save_contact_to_database(user_id, user_name, contact_number, collab_option)

        update.message.reply_text("Thank you for providing your contact information and collaboration option! We will get in touch with you.")
    else:
        update.message.reply_text("There was an issue processing your request. Please try again.")

    return ConversationHandler.END
def save_contact_to_database(user_id, user_name, contact_number, collab_option):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Insert the contact information and collaboration option into the database
        query = "INSERT INTO collab_contacts (user_id, user_name, contact_number, collab_option) VALUES (%s, %s, %s, %s);"
        cursor.execute(query, (user_id, user_name, contact_number, collab_option))
        connection.commit()

        cursor.close()
        connection.close()
    except Exception as e:
        print("Error saving contact information:", e)



#food images function logic


def upload_image(update, context):
    print("Received /upload command")
    user = update.effective_user
    
    # Check if the user is an admin
    if user.id not in ADMIN_USER_IDS:
        context.bot.send_message(user.id, "Sorry, only admin users are allowed to upload images.")
        return

    # Set the user's state to expect an image
    context.user_data["waiting_for_image"] = True
    context.bot.send_message(user.id, "Please send an image.")

def handle_received_image(update, context):
    print("handle_received_image function called")
    print("Received message object:", update.message)
    print("Message text:", update.message.text)
    print("Message photo:", update.message.photo)
    print("Message chat id:", update.message.chat.id)
    user = update.effective_user
    
    # Check if the user is an admin
    if user.id not in ADMIN_USER_IDS:
        context.bot.send_message(user.id, "Sorry, only admin users are allowed to upload images.")
        return
    
    if update.message.photo:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        file = context.bot.get_file(file_id)

        # Download the image and save it to the 'images' directory
        file.download(f"images/{file_id}.jpg")
        image_path = f"images/{file_id}.jpg"

        save_image_to_database(image_path)  # Call a function to save the image path to the database
        
        # Get the Telegram file URL and send the photo
        local_image_path = f"images/{file_id}.jpg"
        with open(local_image_path, 'rb') as photo_file:
            context.bot.send_photo(chat_id=user.id, photo=photo_file)








         # Call a function to save the image URL to the database
        context.bot.send_message(user.id, "Image uploaded successfully.")
    else:
        context.bot.send_message(user.id, "Please send a valid image.")

def save_image_to_database(image_url):
    try:
        print("Saving image to database:", image_url)
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Insert the image URL into the database
        query = "INSERT INTO food_images (image_url) VALUES (%s);"
        cursor.execute(query, (image_url,))
        connection.commit()

        cursor.close()
        connection.close()
    except Exception as e:
        print("Error saving image:", e)
def fetch_latest_images():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Fetch the latest 10 image URLs from the database
        query = "SELECT image_url FROM food_images ORDER BY timestamp DESC LIMIT 10;"
        cursor.execute(query)
        result = cursor.fetchall()

        images = [row[0] for row in result]

        cursor.close()
        connection.close()

        return images
    except Exception as e:
        print("Error fetching images:", e)
        return []
def send_food_images(update, context):
    user_id = update.effective_user.id

    # Fetch the latest 10 uploaded image file IDs from the database
    image_paths = fetch_latest_images()

    if image_paths:
        for image_path in image_paths:
            with open(image_path, 'rb') as photo_file:
                context.bot.send_photo(chat_id=user_id, photo=photo_file)
    else:
        context.bot.send_message(user_id, "No food images available.")




#review function logic


def start_review(update, context) -> int:
    update.message.reply_text("Please enter the name of the restaurant:")
    return ENTER_RESTAURANT_NAME
def enter_restaurant_name(update, context) -> int:
    context.user_data['restaurant_name'] = update.message.text
    update.message.reply_text("Please enter your review:")
    return ENTER_REVIEW
def enter_review(update, context) -> int:
    user_id = update.effective_user.id
    restaurant_name = context.user_data['restaurant_name']
    review_text = update.message.text

    # Save the review to the database (implement save_review_to_database function)
    save_review_to_database(user_id,restaurant_name, review_text)

    update.message.reply_text("Thank you for submitting your review!")

    # Clear user data after review submission
    context.user_data.clear()

    return ConversationHandler.END
def save_review_to_database(user_id,restaurant_name, review_text):
    try:
        if user_id in ADMIN_USER_IDS:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()

            query = "INSERT INTO restaurant_reviews (user_id, restaurant_name, review_text) VALUES (%s, %s, %s);"
            cursor.execute(query, (user_id, restaurant_name, review_text))
            connection.commit()

            cursor.close()
            connection.close()
        else:
            print("Unauthorized user trying to save review.")
    except Exception as e:
        print("Error saving review:", e)


def start_restaurant_review(update, context) -> int:
    context.bot.send_message(chat_id=update.effective_chat.id, text="Please enter the name of the restaurant:tayib")
    return ENTER_RESTAURANT
def fetch_and_show_restaurant_review(update, context):
    restaurant_name = update.message.text

    # Fetch the review from the database (implement fetch_review_from_database function)
    review_text = fetch_review_from_database(restaurant_name)

    if review_text:
        update.message.reply_text(f"Reviews for {restaurant_name}:\n\n{review_text}")
    else:
        update.message.reply_text(f"No reviews found for {restaurant_name}.")

    return ConversationHandler.END
def fetch_review_from_database(restaurant_name):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        query = "SELECT review_text FROM restaurant_reviews WHERE restaurant_name = %s;"
        cursor.execute(query, (restaurant_name,))
        result = cursor.fetchone()

        cursor.close()
        connection.close()

        if result:
            return result[0]
        else:
            return None
    except Exception as e:
        print("Error fetching review:", e)
        return None





#food reels function logic


def send_food_reels(update, context):
    user_id = update.effective_user.id
    context.bot.send_message(user_id, "Enjoy these exciting food reels:")
    # Implement logic to send food reels
    # ...



#recipe function logic


def request_recipe_input(update, context):
    user_id = update.effective_user.id
    context.bot.send_message(user_id, "Please enter which recipe you want 😀 (add recipe in your text)")
    

def handle_text_messages(update, context):
    # Get the user's text message
    user_message = update.message.text.lower()

    # Check if the user's message contains the word 'recipe'
    if 'recipe' in user_message:
        recipe_name = user_message.replace('recipe', '').strip()
        # Here, you can implement a logic to fetch and send the requested recipe
        response = openai.Completion.create(
            engine="text-davinci-002",  # You can use a different engine if needed
            prompt=f"Give me a recipe for {recipe_name}",
            max_tokens=200  # Adjust the number of tokens as needed
        )

        # Get the generated recipe from the ChatGPT response
        generated_recipe = response.choices[0].text.strip()
        # For now, let's just send a placeholder message
        update.message.reply_text(f"Sure! Here's a delicious recipe for {user_message}:{generated_recipe}")


#help function logic

def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm here to help! If you have any questions or need assistance, feel free to ask.")

# Echo handler to respond to user messages


def main():
    # Create an instance of the Updater class
    updater = Updater(TOKEN,use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    # Register command handlers
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help)
    upload_handler=CommandHandler('upload', upload_image)
    dispatcher.add_handler(upload_handler)
    dispatcher.add_handler(MessageHandler(Filters.text("📸 Food Images"), send_food_images))
    
    #recipe dispatcher
    dispatcher.add_handler(MessageHandler(Filters.text("🍰 Recipes"),request_recipe_input ))
    #review handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('review', start_review)],
        states={
            ENTER_RESTAURANT_NAME: [MessageHandler(Filters.text & ~Filters.command, enter_restaurant_name)],
            ENTER_REVIEW: [MessageHandler(Filters.text & ~Filters.command, enter_review)],
        },
        fallbacks=[],
    )
    restaurant_review_handler = ConversationHandler(
    entry_points=[MessageHandler(Filters.text("reviews"), start_restaurant_review)],
    states={
        ENTER_RESTAURANT: [MessageHandler(Filters.text & ~Filters.command, fetch_and_show_restaurant_review)],
    },
    fallbacks=[],
)
    dispatcher.add_handler(restaurant_review_handler)
    dispatcher.add_handler(conv_handler)
    
    

    
    
    # Add the ConversationHandler to the dispatcher
    
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    
    # Register echo handler for all messages
    

    # Start the bot
    updater.start_polling()
    logger.info("Bot started.")

    # Run the bot until you press Ctrl-C
    updater.idle()
if __name__ == '__main__':
    main()
