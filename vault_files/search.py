# external libraries
from backend import database_connection as db
from backend import encryption as enc


def get_user_passwords(user_id):
	sql_query = f"SELECT * FROM '{user_id}-passwords'"
	data = db.c.execute(sql_query).fetchall()
	return data

def decrypt_data(data, key):
	decrypted_data = []
	for row in data:
		new_row = []
		for cell in row:
			try:
				decrypted_cell = enc.decrypt(key, cell).decode("utf-8")
				new_row.append(decrypted_cell)
			except TypeError:	# will be thrown for the id, as id isn't encrypted
				new_row.append(cell)
		decrypted_data.append(new_row)
	return decrypted_data

def remove_prefix(title):
	new_title = ""
	title = title.split("-")[2:]
	for substring in title:
		new_title += substring + "-"
	new_title = new_title[:-1]
	return title

def matching_word(search_term, title):
	score = 0
	for word in search_term.split(" "):
		score += title.count(search_term) * 5
	return score

def same_order(search_term, title):
	search_term, title = search_term.replace(" ", ""), title.replace(" ", "")

	start = 0
	for character in search_term:
		for count in range(start, len(title), 1):
			start = count
			temp = title[count]

			if character == temp:
				break

			if count == (len(title)-1):
				return 0

	return 5	# 5 score

def exact_match(search_term, unprefixed_title):
	if unprefixed_title == search_term:
		return 9999
	else:
		return 0

def sort_and_format(data):
	formatted_data = []
	data = sorted(data, key=lambda d: sorted(d.items()))
	for password in data:
		formatted_data.append(list(password.values())[0])
	return formatted_data


def search(search_term, user_id, key):
	final = []
	data = get_user_passwords(user_id)
	data = decrypt_data(data, key)

	for row in data:
		score = 0
		title = row[1]
		unprefixed_title = remove_prefix(title)[0]

		score += exact_match(search_term, unprefixed_title)
		score += same_order(search_term, unprefixed_title)
		score += matching_word(search_term, unprefixed_title)

		if score >= 5:
			final.append({score:row})

	return sort_and_format(final)
