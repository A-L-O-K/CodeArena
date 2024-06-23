import psycopg2

class DataBase:
    def __init__(self): # initalize the class and establishes connection with the database
        try:
            self.conn = psycopg2.connect(
                database="code_arena",
                user="postgres",
                password="icandoit",
                host="127.0.0.1",
                port="5432"
            )

            self.cur = self.conn.cursor()
            print("Connection succesfully established !")
        
        except Exception:
            print("Error!, Couldnt connect to the database...")
    
    def close_connection(self): # function to close the connection with the database
        try:
            self.conn.close()
            print("Connection Closed Successfully !")
            return 1
        except Exception:
            return 0
    
    def commit(self): # function to commit in the database to save changes
        self.conn.commit()
    

    def do_query(self, query):
        try:
            self.cur.execute(query)
            self.commit()
            
        except Exception as e:
            self.conn.rollback()
            print("An error occurred:", e)
            return 0
    
    def add_question_answer(self, title, description, difficulty, user_id, language, code):
        try:

            # preprocessing to avoid possible problems.. :)
            description = description.replace("'", "`")
            description = description.replace('"', "`")
            
            # Start transaction
            self.conn.autocommit = False
            
            # Step 1: Insert into questions and get the question_id
            insert_question_query = """
                INSERT INTO questions (title, description, difficulty, solution_id, user_id) 
                VALUES (%s, %s, %s, %s, %s)
                RETURNING question_id;
            """
            self.cur.execute(insert_question_query, (f'{title}', f'{description}', difficulty, 0, user_id))
            
            question_id = self.cur.fetchone()[0]

            # Step 2: Insert into solutions using the retrieved question_id
            insert_solution_query = """
                INSERT INTO solutions (language, code, question_id) 
                VALUES (%s, %s, %s)
                RETURNING solution_id;
            """
            self.cur.execute(insert_solution_query, (f'{language}', f'{code}', question_id))
            solution_id = self.cur.fetchone()[0]

            # Step 3: Update questions to set the solution_id
            update_question_query = """
                UPDATE questions 
                SET solution_id = %s 
                WHERE question_id = %s;
            """
            self.cur.execute(update_question_query, (solution_id, question_id))

            # Commit the transaction
            self.conn.commit()
            print("Data inserted into solutions table successfully!")

        except Exception as e:
            # If an error occurs, rollback the transaction
            self.conn.rollback()
            print("An error occurred:", e)

    
