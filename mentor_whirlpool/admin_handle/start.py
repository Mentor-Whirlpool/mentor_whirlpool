from telebot import types


async def admin_start() -> list[str]:
    """
    Should provide a starting point with a ReplyMarkupKeyboard
    It should contain all the following handles

    Parameters
    ----------
    message : telebot.types.Message
        A pyTelegramBotAPI Message type class

    Returns
    -------
    iterable
        Iterable with all handles texts
    """
    return ['Менторы', 'Запросы (админ)', 'Редактировать поддержку', 'Редактировать направления']


async def admin_help() -> str:
    return 'Привет! Ты и сам знаешь, зачем я здесь. Мой функционал:\n\n' \
           '- «Менторы» — возвращает список менторов с количеством студентов по каждой ' \
           'из их тем. При выборе конкретного ментора можно редактировать его темы, ' \
           'студентов, а также удалить этого ментора.\n' \
           '- «Запросы» — показывает висящие запросы от студентов.\n' \
           '- «Редактировать направления» — позволяет добавлять и удалять направления.\n'
