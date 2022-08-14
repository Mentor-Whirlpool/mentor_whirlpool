def get_name(user):
    return user.username if user.username is not None\
           else user.first_name + f" {user.last_name}" if user.last_name is not None else ""


def get_link(user):
    return f'tg://user?id={user.id}'


def get_pretty_mention(user):
    return f'[@{get_name(user)}]({get_link(user)})'


def get_pretty_mention_db(user):
    return f'[@{user["name"]}](tg://user?id={user["chat_id"]})'
