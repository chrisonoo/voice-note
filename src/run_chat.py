from chat import Chat
from services import print_completion


system = ("Jestem wybitnym, błyskotliwym i zabawnym sprzedawcą pomarańczy i mam promocję na kozaki. "
          "Choć jest lato i nikt kozaków nie potrzebuje, to chcę je sprzedać i dobrze zarobić."
          "Odpowiedz w jednym zdaniu ale z polotem.")
user = "Dzień dobry"
model = 4
temperature = 1.3
max_token = 100


def run():
    chat = Chat(system, user, model, temperature, max_token)
    chat_completion = chat.ask()

    print_completion(chat_completion, "message_chat", True, True)


if __name__ == '__main__':
    run()
