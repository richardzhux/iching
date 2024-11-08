
INSERT INTO Interpretations (hexagram_id, section, source, content)
VALUES (
    1,                      -- hexagram_id for 乾卦
    '1.1',                  -- Section
    '《象辞》',               -- Source
    '天行健，君子以自强不息。天道刚健，运行不已。君子观此卦象，从而以天为法，自强不息。乾象征天，六阳爻构成乾卦，为《易经》六十四卦之首。纯阳刚建，其性刚强，其行劲健，大通而至正，兆示大通而有利，但须行正道，方可永远亨通。' 
);


-- Create a table for hexagrams
CREATE TABLE Hexagrams (
    id SERIAL PRIMARY KEY,      -- Unique ID, auto-incremented
    name VARCHAR(50)            -- Name of the hexagram
);

-- Create a table for interpretations, linking to hexagrams by ID
CREATE TABLE Interpretations (
    id SERIAL PRIMARY KEY,            -- Unique ID for each interpretation
    hexagram_id INT REFERENCES Hexagrams(id), -- Foreign key to Hexagrams
    section VARCHAR(10),              -- Section of the interpretation, like "1.1"
    source VARCHAR(50),               -- Source or author of the interpretation
    content TEXT                      -- Text of the interpretation
);
INSERT INTO Hexagrams (name)
VALUES ('乾卦 (Qián Gua)');

INSERT INTO Interpretations (hexagram_id, section, source, content)
VALUES (
    1,                      -- The hexagram_id that corresponds to 乾卦
    '1.1',                  -- Section, e.g., first section of this interpretation
    '《象辞》',               -- Source of the interpretation
    '天行健，君子以自强不息'  -- Content: "The course of heaven is strong, so the superior man must constantly strive for self-improvement."
);


SELECT * FROM Hexagrams;
SELECT section, source, content
FROM Interpretations
WHERE hexagram_id = 1;

SELECT h.name, i.section, i.source, i.content
FROM Hexagrams h
JOIN Interpretations i ON h.id = i.hexagram_id
WHERE i.section = '1.1';




UPDATE Interpretations
SET content = 'Updated content for clarity'
WHERE id = 1;  -- Replace with the specific interpretation ID you want to update

DELETE FROM Interpretations
WHERE id = 1;  -- Replace with the specific interpretation ID you want to delete




SELECT h.name, i.section, i.source, i.content
FROM Hexagrams h
JOIN Interpretations i ON h.id = i.hexagram_id
WHERE i.content LIKE '%self-improvement%';  -- Keyword search

SELECT h.name, COUNT(i.id) AS interpretation_count
FROM Hexagrams h
LEFT JOIN Interpretations i ON h.id = i.hexagram_id
GROUP BY h.name;

CREATE TABLE: Defines tables and their structure.
INSERT INTO: Adds new data to tables.
SELECT: Retrieves data from tables with optional filtering using WHERE.
UPDATE: Modifies existing data.
DELETE: Removes data.
JOIN: Combines data from multiple tables based on a common key (like hexagram_id).
