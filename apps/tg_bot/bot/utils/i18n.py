from __future__ import annotations


TEXTS = {
    "ru": {
        "choose_language": "Выберите язык / Tilni tanlang",
        "language_saved": "Язык сохранён.",
        "change_language": "🌐 Изменить язык",
        "language_menu_hint": "Выберите язык интерфейса:",

        "start_verified": (
            "Здравствуйте.\n\n"
            "Ваш Telegram уже привязан к системе.\n"
            "Компания: {company_name}\n"
            "Заявитель: {employee_name}\n\n"
            "Выберите действие в меню ниже."
        ),
        "start_unverified": (
            "Здравствуйте.\n\n"
            "Чтобы пользоваться ботом, нужно подтвердить номер телефона.\n"
            "Отправьте ваш номер кнопкой ниже.\n\n"
            "Номер будет проверен по базе компаний."
        ),

        "send_contact": "📱 Отправить номер",
        "create_request": "➕ Создать обращение",
        "my_requests": "📄 Мои обращения",
        "help": "ℹ️ Помощь",
        "specify_inn": "🔎 Указать ИНН",
        "send_other_phone": "📱 Отправить другой номер",
        "cancel": "❌ Отмена",
        "back": "⬅️ Назад",
        "skip": "⏭ Пропустить",
        "done": "✔️ Готово",
        "confirm": "✅ Подтвердить",
        "send": "✅ Отправить",

        "unknown_user": "Не удалось определить пользователя Telegram.",
        "contact_data_error": "Не удалось получить данные контакта. Попробуйте еще раз.",
        "send_own_phone": "Пожалуйста, отправьте именно свой номер через кнопку ниже.",
        "phone_not_received": "Номер телефона не получен. Попробуйте отправить контакт еще раз.",
        "send_phone_using_button": "Сейчас нужно отправить номер телефона кнопкой ниже.",
        "phone_verified_success": (
            "✅ Номер успешно подтвержден.\n\n"
            "Компания: {company_name}\n"
            "Заявитель: {employee_name}\n\n"
            "Теперь вы можете пользоваться ботом."
        ),
        "phone_not_found": (
            "Ваш номер не найден в базе компаний.\n\n"
            "Вы можете:\n"
            "• указать ИНН компании\n"
            "• отправить другой номер\n"
            "• отменить действие"
        ),

        "help_text": (
            "Через этого бота можно будет:\n"
            "- отправлять обращения\n"
            "- отслеживать свои обращения\n"
            "- получать помощь по работе системы\n\n"
            "Сейчас подключен базовый этап верификации и главное меню."
        ),
        "verify_first": "Сначала подтвердите номер телефона через /start.",
        "no_requests": "У вас пока нет обращений.",
        "my_recent_requests": "Ваши последние обращения:\n",
        "bind_group_only": "Эта команда работает только в группе.",
        "group_bound": "✅ Эта группа подключена для уведомлений о новых обращениях.",

        "enter_company_inn": "Введите ИНН компании.",
        "send_phone_below": "Отправьте номер телефона кнопкой ниже.",
        "action_cancelled": "Действие отменено.",
        "inn_too_short": "ИНН выглядит слишком коротким. Проверьте и отправьте снова.",
        "company_found": (
            "Компания найдена: {company_name}\n\n"
            "При желании уточните данные компании.\n"
            "Если данные в базе уже верные, можете нажимать «Пропустить»."
        ),
        "company_not_found_enter_name": (
            "Компания с таким ИНН не найдена.\n\n"
            "Введите название компании."
        ),
        "company_name_too_short": "Название компании слишком короткое. Введите нормальное название.",
        "choose_company_region": "Выберите регион компании:",
        "choose_company_district": "Выберите район/город:",
        "send_fio": "Теперь отправьте ФИО заявителя одним сообщением.",
        "region_not_found": "Регион не найден.",
        "district_not_found": "Район не найден.",
        "fio_too_short": "ФИО выглядит слишком коротким. Введите ФИО полностью.",
        "choose_category": "Выберите категорию компании:",
        "category_not_found": "Категория не найдена.",
        "choose_directions": "Выберите направления деятельности.\nМожно выбрать несколько.",
        "updated_list": "Список направлений обновлен.",
        "registration_cancelled": "Регистрация отменена.",
        "registration_preview": (
            "Проверьте данные перед подтверждением.\n\n"
            "ИНН: {inn}\n"
            "Компания: {company_name}\n"
            "ФИО: {fio}\n"
            "Регион: {region_name}\n"
            "Район: {district_name}\n"
            "Категория: {category_name}\n"
            "Направления: {direction_names}"
        ),
        "company_registered_success": (
            "✅ Компания успешно {action_text}.\n\n"
            "Компания: {company_name}\n"
            "ИНН: {inn}\n\n"
            "Теперь вы можете пользоваться ботом."
        ),
        "company_registered_new": "зарегистрирована",
        "company_registered_bound": "привязана",

        "request_step_1_short": "Шаг 1 из 4.\n\nВыберите проблемное направление:",
        "request_step_2_short": "Шаг 2 из 4.\n\nНапишите текст обращения одним сообщением.",
        "request_step_3_short": (
            "Шаг 3 из 4.\n\n"
            "Теперь можете прикрепить файлы.\n"
            "Поддерживаются: PDF, Word, Excel, JPG, PNG.\n"
            "Максимум 10 MB на файл.\n\n"
            "Отправьте один или несколько файлов по очереди, затем нажмите “Готово”."
        ),
        "request_preview_short": (
            "Проверьте обращение перед отправкой.\n\n"
            "Проблемное направление: {problem_direction_name}\n"
            "Файлов: {files_count}\n\n"
            "Текст обращения:\n{description}"
        ),

        "problem_directions_not_configured": "Проблемные направления пока не настроены.",

        "problem_direction_not_found": "Проблемное направление не найдено.",
        "request_description_too_short": "Текст обращения слишком короткий. Опишите проблему чуть подробнее.",
        "file_too_large": "Файл слишком большой. Максимум 10 MB.",
        "photo_too_large": "Фото слишком большое. Максимум 10 MB.",
        "invalid_file_type": "Недопустимый тип файла. Разрешены PDF, Word, Excel, JPG, JPEG, PNG.",
        "file_added": "Файл добавлен: {filename}\nВсего файлов: {count}",
        "photo_added": "Фото добавлено.\nВсего файлов: {count}",
        "upload_file_hint": "На этом шаге отправьте файл или фото, либо нажмите “Готово” / “Пропустить”.",
        "request_preview": (
            "Проверьте обращение перед отправкой.\n\n"
            "Проблемное направление: {problem_direction_name}\n"
            "Категория: {category_name}\n"
            "Регион: {region_name}\n"
            "Район: {district_name}\n"
            "Направления: {direction_names}\n"
            "Файлов: {files_count}\n\n"
            "Текст обращения:\n{description}"
        ),
        "request_cancelled": "Создание обращения отменено.",
        "request_created_success": (
            "✅ Обращение успешно создано.\n\n"
            "Номер обращения: {request_number}\n"
            "Статус: {status}\n\n"
            "Ваше обращение зарегистрировано в системе."
        ),

        "status_new": "Новое",
        "status_registered": "Зарегистрировано",
        "status_sent_for_resolution": "На резолюции",
        "status_assigned": "Назначено исполнителю",
        "status_in_progress": "В работе",
        "status_waiting": "Ожидает ответа",
        "status_done": "Обработано",
        "status_cancelled": "Отменено",
        "main_menu": "🏠 Главное меню",
        "session_recovered": (
            "Похоже, текущий шаг устарел, был отменён или прерван.\n"
            "Я вернул вас в рабочее меню."
        ),
        "unknown_input_recovered": (
            "Я не понял это действие в текущем шаге.\n"
            "Вернул вас в безопасное меню, чтобы можно было продолжить."
        ),
        "callback_expired_alert": "Это действие устарело. Я открыл актуальное меню.",
        "action_recovered_short": "Действие восстановлено.",
        "unexpected_error_recovered": (
            "Произошла ошибка, но бот не завис.\n"
            "Я вернул вас в безопасное меню."
        ),
    },
    "uz": {
        "choose_language": "Tilni tanlang / Выберите язык",
        "language_saved": "Til saqlandi.",
        "change_language": "🌐 Tilni o‘zgartirish",
        "language_menu_hint": "Interfeys tilini tanlang:",

        "start_verified": (
            "Salom.\n\n"
            "Telegram profilingiz tizimga ulangan.\n"
            "Kompaniya: {company_name}\n"
            "Arizachi: {employee_name}\n\n"
            "Quyidagi menyudan amalni tanlang."
        ),
        "start_unverified": (
            "Salom.\n\n"
            "Botdan foydalanish uchun telefon raqamingizni tasdiqlashingiz kerak.\n"
            "Quyidagi tugma orqali raqamingizni yuboring.\n\n"
            "Raqam kompaniyalar bazasi bo‘yicha tekshiriladi."
        ),

        "send_contact": "📱 Raqamni yuborish",
        "create_request": "➕ Murojaat yaratish",
        "my_requests": "📄 Mening murojaatlarim",
        "help": "ℹ️ Yordam",
        "specify_inn": "🔎 STIRni kiritish",
        "send_other_phone": "📱 Boshqa raqam yuborish",
        "cancel": "❌ Bekor qilish",
        "back": "⬅️ Orqaga",
        "skip": "⏭ O‘tkazib yuborish",
        "done": "✔️ Tayyor",
        "confirm": "✅ Tasdiqlash",
        "send": "✅ Yuborish",

        "unknown_user": "Telegram foydalanuvchisini aniqlab bo‘lmadi.",
        "contact_data_error": "Kontakt ma’lumotlarini olib bo‘lmadi. Qayta urinib ko‘ring.",
        "send_own_phone": "Iltimos, quyidagi tugma orqali aynan o‘zingizning raqamingizni yuboring.",
        "phone_not_received": "Telefon raqami olinmadi. Kontaktni yana yuborib ko‘ring.",
        "send_phone_using_button": "Hozir telefon raqamini quyidagi tugma orqali yuborish kerak.",
        "phone_verified_success": (
            "✅ Raqam muvaffaqiyatli tasdiqlandi.\n\n"
            "Kompaniya: {company_name}\n"
            "Arizachi: {employee_name}\n\n"
            "Endi siz botdan foydalanishingiz mumkin."
        ),
        "phone_not_found": (
            "Sizning raqamingiz kompaniyalar bazasidan topilmadi.\n\n"
            "Siz quyidagilardan birini tanlashingiz mumkin:\n"
            "• kompaniya STIRini kiritish\n"
            "• boshqa raqam yuborish\n"
            "• amalni bekor qilish"
        ),

        "help_text": (
            "Ushbu bot orqali siz:\n"
            "- murojaat yuborishingiz\n"
            "- murojaatlaringizni kuzatishingiz\n"
            "- tizim bo‘yicha yordam olishingiz mumkin\n\n"
            "Hozircha bazaviy tasdiqlash va asosiy menyu ulangan."
        ),
        "verify_first": "Avval telefon raqamingizni /start orqali tasdiqlang.",
        "no_requests": "Sizda hali murojaatlar yo‘q.",
        "my_recent_requests": "So‘nggi murojaatlaringiz:\n",
        "bind_group_only": "Bu buyruq faqat guruhda ishlaydi.",
        "group_bound": "✅ Ushbu guruh yangi murojaatlar bo‘yicha bildirishnomalar uchun ulandi.",

        "enter_company_inn": "Kompaniya STIRini kiriting.",
        "send_phone_below": "Telefon raqamini quyidagi tugma orqali yuboring.",
        "action_cancelled": "Amal bekor qilindi.",
        "inn_too_short": "STIR juda qisqa ko‘rinmoqda. Tekshirib, qayta yuboring.",
        "company_found": (
            "Kompaniya topildi: {company_name}\n\n"
            "Istasangiz, kompaniya ma’lumotlarini aniqlashtirishingiz mumkin.\n"
            "Agar bazadagi ma’lumotlar to‘g‘ri bo‘lsa, “O‘tkazib yuborish”ni bosing."
        ),
        "company_not_found_enter_name": (
            "Bunday STIR bilan kompaniya topilmadi.\n\n"
            "Kompaniya nomini kiriting."
        ),
        "company_name_too_short": "Kompaniya nomi juda qisqa. To‘g‘ri nom kiriting.",
        "choose_company_region": "Kompaniya viloyatini tanlang:",
        "choose_company_district": "Kompaniya tumani/shahrini tanlang:",
        "send_fio": "Endi arizachining F.I.Sh.ni bitta xabarda yuboring.",
        "region_not_found": "Viloyat topilmadi.",
        "district_not_found": "Tuman topilmadi.",
        "fio_too_short": "F.I.Sh. juda qisqa ko‘rinmoqda. To‘liq kiriting.",
        "choose_category": "Kompaniya kategoriyasini tanlang:",
        "category_not_found": "Kategoriya topilmadi.",
        "choose_directions": "Faoliyat yo‘nalishlarini tanlang.\nBir nechtasini tanlash mumkin.",
        "updated_list": "Yo‘nalishlar ro‘yxati yangilandi.",
        "registration_cancelled": "Ro‘yxatdan o‘tish bekor qilindi.",
        "registration_preview": (
            "Tasdiqlashdan oldin ma’lumotlarni tekshiring.\n\n"
            "STIR: {inn}\n"
            "Kompaniya: {company_name}\n"
            "F.I.Sh.: {fio}\n"
            "Viloyat: {region_name}\n"
            "Tuman/shahar: {district_name}\n"
            "Kategoriya: {category_name}\n"
            "Yo‘nalishlar: {direction_names}"
        ),
        "company_registered_success": (
            "✅ Kompaniya muvaffaqiyatli {action_text}.\n\n"
            "Kompaniya: {company_name}\n"
            "STIR: {inn}\n\n"
            "Endi siz botdan foydalanishingiz mumkin."
        ),
        "company_registered_new": "ro‘yxatdan o‘tkazildi",
        "company_registered_bound": "biriktirildi",

        "request_step_1_short": "1/4-qadam.\n\nMuammoli yo‘nalishni tanlang:",
        "request_step_2_short": "2/4-qadam.\n\nMurojaat matnini bitta xabarda yozing.",
        "request_step_3_short": (
            "3/4-qadam.\n\n"
            "Endi fayllarni biriktirishingiz mumkin.\n"
            "Qo‘llab-quvvatlanadi: PDF, Word, Excel, JPG, PNG.\n"
            "Har bir fayl uchun maksimal hajm 10 MB.\n\n"
            "Bir yoki bir nechta faylni ketma-ket yuboring, so‘ng “Tayyor”ni bosing."
        ),
        "request_preview_short": (
            "Yuborishdan oldin murojaatni tekshiring.\n\n"
            "Muammoli yo‘nalish: {problem_direction_name}\n"
            "Fayllar: {files_count}\n\n"
            "Murojaat matni:\n{description}"
        ),

        "problem_directions_not_configured": "Muammoli yo‘nalishlar hali sozlanmagan.",

        "problem_direction_not_found": "Muammoli yo‘nalish topilmadi.",
        "request_description_too_short": "Murojaat matni juda qisqa. Muammoni biroz batafsilroq yozing.",
        "file_too_large": "Fayl juda katta. Maksimal hajm 10 MB.",
        "photo_too_large": "Rasm juda katta. Maksimal hajm 10 MB.",
        "invalid_file_type": "Noto‘g‘ri fayl turi. PDF, Word, Excel, JPG, JPEG, PNG fayllari ruxsat etiladi.",
        "file_added": "Fayl qo‘shildi: {filename}\nJami fayllar: {count}",
        "photo_added": "Rasm qo‘shildi.\nJami fayllar: {count}",
        "upload_file_hint": "Bu bosqichda fayl yoki rasm yuboring, yoki “Tayyor” / “O‘tkazib yuborish”ni bosing.",
        "request_preview": (
            "Yuborishdan oldin murojaatni tekshiring.\n\n"
            "Muammoli yo‘nalish: {problem_direction_name}\n"
            "Kategoriya: {category_name}\n"
            "Viloyat: {region_name}\n"
            "Tuman: {district_name}\n"
            "Yo‘nalishlar: {direction_names}\n"
            "Fayllar: {files_count}\n\n"
            "Murojaat matni:\n{description}"
        ),
        "request_cancelled": "Murojaat yaratish bekor qilindi.",
        "request_created_success": (
            "✅ Murojaat muvaffaqiyatli yaratildi.\n\n"
            "Murojaat raqami: {request_number}\n"
            "Status: {status}\n\n"
            "Murojaatingiz tizimda ro‘yxatdan o‘tkazildi."
        ),

        "status_new": "Yangi",
        "status_registered": "Ro‘yxatdan o‘tkazilgan",
        "status_sent_for_resolution": "Rezolyutsiyada",
        "status_assigned": "Ijrochiga tayinlangan",
        "status_in_progress": "Jarayonda",
        "status_waiting": "Javob kutilmoqda",
        "status_done": "Ko‘rib chiqilgan",
        "status_cancelled": "Bekor qilingan",
        "main_menu": "🏠 Bosh menyu",
        "session_recovered": (
            "Joriy bosqich eskirgan, bekor qilingan yoki uzilib qolgan ko‘rinadi.\n"
            "Siz ishchi menyuga qaytarildingiz."
        ),
        "unknown_input_recovered": (
            "Joriy bosqichda bu amal tushunilmadi.\n"
            "Davom etishingiz uchun siz xavfsiz menyuga qaytarildingiz."
        ),
        "callback_expired_alert": "Bu amal eskirgan. Men sizga amaldagi menyuni ochdim.",
        "action_recovered_short": "Amal tiklandi.",
        "unexpected_error_recovered": (
            "Xatolik yuz berdi, lekin bot to‘xtab qolmadi.\n"
            "Siz xavfsiz menyuga qaytarildingiz."
        ),
    },
}


def normalize_lang(lang: str | None) -> str:
    lang = (lang or "ru").lower()
    return "uz" if lang.startswith("uz") else "ru"


def tr(lang: str | None, key: str, **kwargs) -> str:
    lang = normalize_lang(lang)
    text = TEXTS.get(lang, TEXTS["ru"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def get_i18n_attr(obj, base_field: str, lang: str | None, fallback: str | None = None) -> str:
    if obj is None:
        return ""

    lang = normalize_lang(lang)
    localized_field = f"{base_field}_{lang}"

    if hasattr(obj, localized_field):
        value = getattr(obj, localized_field, None)
        if value:
            return str(value)

    if hasattr(obj, base_field):
        value = getattr(obj, base_field, None)
        if value:
            return str(value)

    if fallback and hasattr(obj, fallback):
        value = getattr(obj, fallback, None)
        if value:
            return str(value)

    return str(obj)


def translate_request_status(status: str, lang: str | None) -> str:
    mapping = {
        "new": "status_new",
        "registered": "status_registered",
        "sent_for_resolution": "status_sent_for_resolution",
        "assigned": "status_assigned",
        "in_progress": "status_in_progress",
        "waiting": "status_waiting",
        "done": "status_done",
        "cancelled": "status_cancelled",
    }
    key = mapping.get(status)
    if not key:
        return status or "—"
    return tr(lang, key)