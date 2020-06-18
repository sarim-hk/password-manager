from PyQt5 import QtCore, QtGui, QtWidgets, uic
from backend import database_connection as db
from backend import encryption as enc
import sqlite3, dialog

class Preview(QtWidgets.QWidget):
	changeMade = QtCore.pyqtSignal()

	def __init__(self, key, password_row_data, user_id):
		super().__init__()
		uic.loadUi("ui_files/vault/preview.ui", self)

		self._password_row_data = password_row_data
		self._user_id = user_id
		self._key = key

		self.titleLabel.setText(password_row_data[1])

		self.expandButton.clicked.connect(self.expand)
		self.deleteButton.clicked.connect(self.remove)
		self.editButton.clicked.connect(self.edit)


	@property
	def user_id(self):
		return self._user_id


	@property
	def id(self):
		return self._password_row_data[0]


	@property
	def key(self):
		return self._key

	def remove(self):
		sql_query = f"SELECT name FROM sqlite_master WHERE name LIKE '{self.user_id}-folder-%' ORDER BY name ASC"
		folders = db.c.execute(sql_query).fetchall()
		
		for folder in folders:	
			sql_query = f"DELETE FROM '{folder[0]}' WHERE PASSWORD_ID = ?"
			db.c.execute(sql_query, (self.id,))		# remove it from any folders that exist
			db.conn.commit()

		sql_query = f"DELETE FROM '{self.user_id}-passwords' WHERE ID = ?"
		db.c.execute(sql_query, (self.id,))	# remove it from the passwords table
		db.conn.commit()

		self.changeMade.emit()


	def expand(self):
		Dialog = expandDialog(self.key, self._password_row_data)
		Dialog.exec_()


	def edit(self):
		Dialog = enterDataDialog(self.user_id, self.key, password_row_data=self._password_row_data)
		Dialog.exec_()

		details = Dialog.details

		sql_query = f"""
					UPDATE '{self.user_id}-passwords'
					SET TITLE = ?,
					URL = ?,
					USERNAME = ?,
					EMAIL = ?,
					PASSWORD = ?,
					OTHER = ?
					WHERE ID = ?
					"""
		try:
			db.c.execute(sql_query, (details["title"], details["url"], details["username"], details["email"], details["password"], details["other"], self.id))
			db.conn.commit()
		except TypeError:	# user exited dialog without entering anything
			return

		self.changeMade.emit()


class expandDialog(QtWidgets.QDialog):
	def __init__(self, key, password_row_data):
		super().__init__()
		uic.loadUi("ui_files/vault/expandDialog.ui", self)
		self._key = key

		self.displayDetails(password_row_data)


	@property
	def key(self):
		return self._key

	def displayDetails(self, password_row_data):
		self.titleLabel.setText(password_row_data[1])
		self.urlLabel.setText(password_row_data[2])
		self.usernameLabel.setText(password_row_data[3])
		self.emailLabel.setText(password_row_data[4])
		self.passwordLabel.setText(password_row_data[5])
		self.otherLabel.setText(password_row_data[6])

		self.show()


class enterFolderDialog(QtWidgets.QDialog):
	def __init__(self, key, folderName=""):
		super().__init__()
		uic.loadUi("ui_files/vault/enterFolderDialog.ui", self)

		self.setWindowTitle("Enter folder name:")
		self.lineEdit.setText(folderName)

		self.OKButton = self.findChild(QtWidgets.QPushButton, "OKButton")
		self.OKButton.clicked.connect(self.validateText)

		self.show()


	def saveText(self):
		self._text = self.lineEdit.text()
		self.close()


	def validateText(self):
		if "/" in self.lineEdit.text():
			Dialog = dialog.Dialog("You cannot use the '/' character!", dialogName="Invalid character used.")
			Dialog.exec_()
		else:
			self.saveText()


	@property
	def text(self):
		return f"{self._text}/"


class enterDataDialog(QtWidgets.QDialog):
	def __init__(self, user_id, key, password_row_data=["", "", "", "", "", "", ""]):
		super().__init__()
		uic.loadUi("ui_files/vault/enterDataDialog.ui", self)

		self.titleEdit.setText(password_row_data[1])
		self.urlEdit.setText(password_row_data[2])
		self.usernameEdit.setText(password_row_data[3])
		self.emailEdit.setText(password_row_data[4])
		self.passwordEdit.setText(password_row_data[5])
		self.otherEdit.setText(password_row_data[6])

		self.setWindowTitle("Enter details:")

		self.title_cache = password_row_data[1]
		self._user_id = user_id
		self._key = key

		self.OKButton = self.findChild(QtWidgets.QPushButton, "OKButton")
		self.OKButton.clicked.connect(self.validateText)

		self.show()

	
	@property
	def key(self):
		return self._key

	@property
	def details(self):
		try:
			return self._data_dict
		except AttributeError:	# user exited dialog without entering anything
			return

	def validateText(self):
		if self.titleEdit.text() == "":
			Dialog = dialog.Dialog("Title cannot be Empty!", dialogName="Empty field.")
			Dialog.exec_()
			return
	
		elif self.title_cache == self.titleEdit.text():	# title hasn't changed - no point in validating it
			self.saveDetails()
			return

		if "/" in self.titleEdit.text():	# validate for '/' character
			Dialog = dialog.Dialog("You cannot use the '/' character in your title!", dialogName="Invalid character used.")
			Dialog.exec_()
			return
		
		sql_query = f"SELECT TITLE FROM '{self._user_id}-passwords'"
		tempTitles = db.c.execute(sql_query).fetchall()

		for title in tempTitles:
			decryptedTitle = enc.decrypt(self.key, title[0])
			if decryptedTitle.decode("utf-8") == self.titleEdit.text():

					Dialog = dialog.Dialog("This title has already been used!", dialogName="Existing title.")
					Dialog.exec_()
					return
			
		self.saveDetails()

	def saveDetails(self):
		data_dict = {}
		
		data_dict["title"] = enc.encrypt(self.key, self.titleEdit.text())
		data_dict["url"] = enc.encrypt(self.key, self.urlEdit.text())
		data_dict["username"] = enc.encrypt(self.key, self.usernameEdit.text())
		data_dict["email"] = enc.encrypt(self.key, self.emailEdit.text())
		data_dict["password"] = enc.encrypt(self.key, self.passwordEdit.text())
		data_dict["other"] = enc.encrypt(self.key, self.otherEdit.text())
		self._data_dict = data_dict
		self.close()


class Vault(QtWidgets.QMainWindow):	
	def __init__(self, user_id, password_given):
		super().__init__()
		uic.loadUi("ui_files/vault/vault.ui", self)

		self._user_id = user_id
		self.preview_dict = {}
		self._key = enc.create_key(password_given)

		self.deleteFolderButton.clicked.connect(self.deleteFolder)
		self.editFolderButton.clicked.connect(self.editFolder)
		self.Explorer.currentItemChanged.connect(self.drawFolderPreviews)
		self.newFolder.triggered.connect(self.addFolder)
		self.newEntry.triggered.connect(self.addEntry)

		self.drawPreviews(suppliedPreviewData=False)
		self.drawExplorer()
		self.Explorer.setColumnWidth(0, round(self.Explorer.width()*.75))

		self.show()


	@property
	def key(self):
		return self._key


	@property
	def user_id(self):
		return self._user_id


	def getCurrentItemPath(self, passwordsEnabled=False):
		path_array = []
		final_path = ""

		item = self.Explorer.currentItem()

		if item is None:	# if user hasn't selected anything
			return	

		if item.text(1) != "Folder" and passwordsEnabled == False:
			item = self.Explorer.currentItem().parent()	# selects the folder the password is in, rather than the password itself
		else:
			pass

		try:
			while True:
				item2 = item.parent()
				path_array.append(f"{item.text(0)}/")
				item = item2
		except AttributeError:
			path_array.reverse()

			for subpath in path_array:
				final_path += subpath	
			final_path = f"{self.user_id}-folder-{final_path}"
			
			return final_path


	def drawFolderPreviews(self):	
		suppliedPreviewData = []

		final_path = self.getCurrentItemPath()

		sql_query = f"SELECT PASSWORD_ID FROM '{final_path}'"
		try:
			password_ids = db.c.execute(sql_query).fetchall()
		except sqlite3.OperationalError:	# thrown when an event is called that gets rid of the current selection (i.e. creating a new folder)
			return

		for password in password_ids:
			sql_query = f"SELECT * FROM '{self.user_id}-passwords' WHERE ID = ?"
			data = db.c.execute(sql_query, (password[0],)).fetchone()
			suppliedPreviewData.append(data)

		self.drawPreviews(suppliedPreviewData=suppliedPreviewData)

		
	def append_to_tree(self, node, c):
		if not c:
			return

		if c[0] not in node:
			node[c[0]] = {}

		self.append_to_tree(node[c[0]], c[1:])	


	def drawExplorer(self):	
		folderArray = []
		folderArray2 = []
		root = {}

		self.Explorer.clear()
		self.Explorer.setHeaderLabels(["Name", "Type"])

		sql_query = f"SELECT name FROM sqlite_master WHERE name LIKE '{self.user_id}-folder-%' ORDER BY name ASC"
		folders = db.c.execute(sql_query).fetchall()

		for folder in folders:
			folderArray.append(folder[0])

		folders = folderArray

		for folder in folderArray:
			sql_query = f"SELECT PASSWORD_ID FROM '{folder}'"
			password_ids = db.c.execute(sql_query).fetchall()

			folderArray2.append(folder.strip("/"))
			for password in password_ids:
				sql_query = f"SELECT TITLE FROM '{self.user_id}-passwords' WHERE ID = ?"
				url = db.c.execute(sql_query, (password[0],)).fetchone()
				
				url = enc.decrypt(self.key, url[0]).decode("utf-8")
				folderArray2.append(f"{folder}{url}".strip("/"))

		for path in folderArray2:
			self.append_to_tree(root, path.split('/'))

		self.fill_explorer(self.Explorer.invisibleRootItem(), root, folders)
		self.Explorer.expandAll()


	def fill_explorer(self, explorer_widget, dict_tree, folders):
		if type(dict_tree) is dict:
			for key, val in dict_tree.items():		
				child = QtWidgets.QTreeWidgetItem()
				child.setText(0, key.replace(f"{self.user_id}-folder-", ""))
	
				for folder in folders:
					if key in folder:
						Type = "Folder"
						break
					else:
						Type = "Password"

				child.setText(1, Type)
				explorer_widget.addChild(child)
				self.fill_explorer(child, val, folders)


	def drawPreviews(self, suppliedPreviewData=False):
		x, y = 0, 0
		max_preview_width = 4 #the previews are 200px long

		for i in reversed(range(self.gridLayout.count())): 	# clears the grid
				self.gridLayout.itemAt(i).widget().setParent(None)

		if suppliedPreviewData == False:
			sql_query = f"SELECT * FROM '{self.user_id}-passwords'"
			data = db.c.execute(sql_query).fetchall()
		else:
			data = suppliedPreviewData
			del suppliedPreviewData

		for preview_data in data:
			decrypted_preview_data = []
			for column in preview_data:
				if type(column) != int:
					column = enc.decrypt(self.key, column).decode("utf-8")
				decrypted_preview_data.append(column)
			

			if x == max_preview_width:
				x = 0
				y += 1

			tempPreview = Preview(self.key, decrypted_preview_data, self.user_id)
			tempPreview.changeMade.connect(self.drawPreviewsExplorer)
			self.preview_dict[tempPreview.id] = tempPreview
			self.gridLayout.addWidget(tempPreview, y, x)

			x += 1


	def drawPreviewsExplorer(self):
		self.drawExplorer()
		if self.getCurrentItemPath():
			self.drawFolderPreviews()
		else:
			self.drawPreviews()


	def addFolder(self):
		Dialog = enterFolderDialog(self.key)
		Dialog.exec_()

		try:
			folderName = Dialog.text
		except (UnboundLocalError, AttributeError): #user exited dialog, didn't successfully input
			return

		path = self.getCurrentItemPath()
		if path is None or path == f"{self.user_id}-folder-All/":
			folderName = f"{self.user_id}-folder-{folderName}"
		else:
			folderName = f"{path}{folderName}"
		
		sql_query = f"""
		CREATE TABLE '{folderName}' (
		PASSWORD_ID INTEGER PRIMARY KEY
		);"""

		try:
			db.c.execute(sql_query)
			db.conn.commit()
		except sqlite3.OperationalError:
			Dialog = dialog.Dialog("Folder already exists!", dialogName="Pre-existing folder.")
			Dialog.exec_()

		Dialog.close()

		self.drawPreviewsExplorer()


	def deleteFolder(self):
		path = self.getCurrentItemPath()
		if path is None or path == f"{self.user_id}-folder-All/":
			Dialog = dialog.Dialog("You cannot delete this folder!", dialogName="Invalid folder.")
			Dialog.exec_()
			return

		sql_query = f"SELECT name FROM sqlite_master WHERE name LIKE '{path}%' ORDER BY name ASC"
		folders = db.c.execute(sql_query).fetchall()

		for folder in folders:
			sql_query = f"DROP TABLE '{folder[0]}'"
			db.c.execute(sql_query)
			db.conn.commit()

		self.drawPreviewsExplorer()


	def editFolder(self):
		final = ""
		path = self.getCurrentItemPath()
		if path is None or path == f"{self.user_id}-folder-All/":
			Dialog = dialog.Dialog("You cannot edit this folder!", dialogName="Invalid folder.")
			Dialog.exec_()
			return

		else:
			Dialog = enterFolderDialog(self.key, folderName=self.Explorer.currentItem().text(0))
			Dialog.exec_()
			try:
				folderName = Dialog.text
			except (UnboundLocalError, AttributeError): #user exited dialog, didn't successfully input
				return

			newPath = path.strip("http://").strip("https://").split("/")
			if len(newPath) == 2:	# not a subdirectory
				newPath = path.split("-")
				newPath[-1] = folderName
				for subpath in newPath:
					final += f"{subpath}-"
				final = final[:-1]

			else:
				newPath[-2] = folderName
				for subpath in newPath:
					final += f"{subpath}/"

		sql_query = f"""ALTER TABLE '{path}'
 					RENAME TO '{final}';
		  			"""
		db.c.execute(sql_query)
		db.conn.commit()

		self.drawPreviewsExplorer()


	def addEntry(self):	
		Dialog = enterDataDialog(self.user_id, self.key)
		Dialog.exec_()

		try:
			details = Dialog.details
		except (UnboundLocalError, AttributeError):	#user exited dialog, didn't successfully input
			return

		sql_query = f"""
					INSERT OR REPLACE INTO '{self.user_id}-passwords'
					VALUES(?,?,?,?,?,?,?)
					"""
		try:
			db.c.execute(sql_query, (None, details["title"], details["url"], details["username"], details["email"], details["password"], details["other"]))
			db.conn.commit()
		except TypeError:	# user exited without typing anything
			return

		path = self.getCurrentItemPath()
		if path is None:
			path = f"{self.user_id}-folder-All/"

		sql_query = f"""
					INSERT OR REPLACE INTO '{path}'
					VALUES(?)
					"""
		db.c.execute(sql_query, (db.c.lastrowid,))
		db.conn.commit()

		sql_query = f"""
					INSERT OR REPLACE INTO '{self.user_id}-folder-All/'
					VALUES(?)
					"""
		db.c.execute(sql_query, (db.c.lastrowid,))
		db.conn.commit()

		self.drawPreviewsExplorer()
		

if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication(sys.argv)
	window = Vault(1, "sarim786")
	app.exec_()