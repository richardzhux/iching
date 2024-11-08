import psycopg2

# hash it
conn = psycopg2.connect(
    dbname="your_database_name",
    user="your_username",
    password="your_password",
    host="localhost",
    port="5432",
)

cursor = conn.cursor()

# Define your SQL query
query = """
SELECT section, source, content
FROM Interpretations
WHERE hexagram_id = %s
"""

# Execute the query with a specific hexagram_id
cursor.execute(query, (1,))  # Replace 1 with the desired hexagram_id
results = cursor.fetchall()


# Print out each interpretation
for section, source, content in results:
    print(f"Section: {section}")
    print(f"Source: {source}")
    print("Content:")
    print(content)  # This will preserve multi-paragraph formatting
    print("\n" + "-" * 40 + "\n")  # Divider for readability

# Close the cursor and connection
cursor.close()
conn.close()
