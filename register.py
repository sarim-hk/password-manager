from argon2 import PasswordHasher
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from backend import database_connection as db
import sqlite3
import login, dialog


class Register(QtWidgets.QMainWindow):
	def __init__(self):
		super(Register, self).__init__()
		uic.loadUi("ui_files/register/register.ui", self)
		
		self._passwordHidden = True

		self.showPassButton = self.findChild(QtWidgets.QPushButton, "showPassButton") # Find the button
		self.showPassButton.clicked.connect(self.unhidePassword)

		self.submitButton = self.findChild(QtWidgets.QPushButton, "submitButton") # Find the button
		self.submitButton.clicked.connect(self.validateInputs)

		self.goToLoginButton = self.findChild(QtWidgets.QPushButton, "goToLoginButton") # Find the button
		self.goToLoginButton.clicked.connect(self.goToLogin)

		self.show()

	def unhidePassword(self):
		if self._passwordHidden is True:
			self.passwordEdit.setEchoMode(QtWidgets.QLineEdit.Normal)
			self.passwordRetypeEdit.setEchoMode(QtWidgets.QLineEdit.Normal)
			self.showPassButton.setText("Hide Password")
			self._passwordHidden = False
		else:
			self.passwordEdit.setEchoMode(QtWidgets.QLineEdit.Password)
			self.passwordRetypeEdit.setEchoMode(QtWidgets.QLineEdit.Password)
			self.showPassButton.setText("Show Password")
			self._passwordHidden = True

	def validateInputs(self):
		username = self.usernameEdit.text()
		password = self.passwordEdit.text()
		passwordRetype = self.passwordRetypeEdit.text()
		
		# validate for username length
		if len(username) <5 or len(username) > 30:
			Dialog = dialog.Dialog("Username must be 5 - 30 characters long!", dialogName="Incorrect username.")
			Dialog.exec_()
			self.usernameEdit.setText("")
			return

		# validate for password length
		elif len(password) <5 or len(password) > 30 or len(passwordRetype) <5 or len(passwordRetype) > 30:
			Dialog = dialog.Dialog("Password must be 5 - 30 characters long!", dialogName="Incorrect password.")
			Dialog.exec_()
			self.passwordEdit.setText("")
			self.passwordRetypeEdit.setText("")
			return

		# validate for matching passwords
		elif password != passwordRetype:
			Dialog = dialog.Dialog("Passwords must match!", dialogName="Passwords do not match.")
			Dialog.exec_()
			self.passwordEdit.setText("")
			self.passwordRetypeEdit.setText("")
			return		

		# validate for existing account
		sql_query = f"SELECT USERNAME FROM user_data WHERE USERNAME = '{username}'"
		retrieved_data = db.c.execute(sql_query)
		try:
			retrieved_data.fetchone()[0]
			Dialog = dialog.Dialog("Username already registered!", dialogName="Account already exists.")
			Dialog.exec_()
			return
		except TypeError:
			password = PasswordHasher().hash(password)

		# insert username & password into database
		sql_query = f"""
		INSERT INTO user_data(USERNAME, PASSWORD)
		VALUES('{username}','{password}');
		"""
		db.c.execute(sql_query)
		db.conn.commit()

		# get user's id
		sql_query = f"SELECT USER_ID FROM user_data WHERE USERNAME = '{username}'"
		user_id = db.c.execute(sql_query).fetchone()[0]

		# create user's passwords table
		sql_query = f"""
		CREATE TABLE {user_id}_passwords (
		ID INTEGER PRIMARY KEY,
		URL    		TEXT    (1, 100),
		USERNAME    TEXT    (1, 100),
		EMAIL   	TEXT    (1, 100),
		PASSWORD   	TEXT    (1, 100),
		OTHER  		TEXT    (1, 100)
		);"""
		db.c.execute(sql_query)
		db.conn.commit()

		#create user's notes table
		sql_query = f"""
		CREATE TABLE {user_id}_notes (
		ID INTEGER PRIMARY KEY,
		TITLE    	TEXT    (1, 100),
		CONTENT   	TEXT    (1, 100)
		);"""
		db.c.execute(sql_query)
		db.conn.commit()		

		Dialog = dialog.Dialog("Account registered successfully!", dialogName="Success.")
		Dialog.exec_()

		self.usernameEdit.setText("")
		self.passwordEdit.setText("")
		self.passwordRetypeEdit.setText("")

	def goToLogin(self):
		self.window = login.Login()
		self.close()