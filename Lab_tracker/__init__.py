import pymysql

pymysql.version_info = (2, 2, 1, "final", 0)  # satisfies Django's driver version check
pymysql.install_as_MySQLdb()