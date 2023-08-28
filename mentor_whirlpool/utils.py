def get_name(user):
    return markdown_escape(user.username) if user.username is not None\
           else markdown_escape(user.first_name + f" {user.last_name}") if user.last_name is not None else ""


def get_link(user):
    return f'tg://user?id={user.id}'


def get_pretty_mention(user):
    return f'[@{user.username}]({get_link(user)})'


def get_pretty_mention_db(user):
    return f'[@{user["name"]}](tg://user?id={user["chat_id"]})'

def markdown_escape(text):
    special_characters = set('#*>`~_')
    return "".join('\\' + c if c in special_characters or c == '\\' else c for c in text)
