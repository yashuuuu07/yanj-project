-- ============================================================
-- QUIZ FEATURE SQL — Run this in the Supabase SQL Editor
-- ============================================================

-- 1. Create quiz_questions table
CREATE TABLE IF NOT EXISTS public.quiz_questions (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    course_id   UUID REFERENCES public.courses(id) ON DELETE CASCADE,
    subject     TEXT NOT NULL,
    question    TEXT NOT NULL,
    option_a    TEXT NOT NULL,
    option_b    TEXT NOT NULL,
    option_c    TEXT NOT NULL,
    option_d    TEXT NOT NULL,
    correct_answer TEXT NOT NULL CHECK (correct_answer IN ('A','B','C','D')),
    created_by  UUID REFERENCES public.users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create quiz_attempts table
CREATE TABLE IF NOT EXISTS public.quiz_attempts (
    id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id          UUID REFERENCES public.users(id) ON DELETE CASCADE,
    course_id        UUID REFERENCES public.courses(id) ON DELETE CASCADE,
    question_id      UUID REFERENCES public.quiz_questions(id) ON DELETE CASCADE,
    selected_answer  TEXT NOT NULL CHECK (selected_answer IN ('A','B','C','D')),
    is_correct       BOOLEAN NOT NULL,
    emotion          TEXT,
    confidence_score FLOAT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Enable RLS
ALTER TABLE public.quiz_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quiz_attempts  ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policies for quiz_questions
-- Everyone authenticated can read questions
CREATE POLICY "Authenticated users can read quiz questions"
    ON public.quiz_questions FOR SELECT
    TO authenticated USING (true);

-- Only admins can insert
CREATE POLICY "Admins can insert quiz questions"
    ON public.quiz_questions FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM public.users
        WHERE id = auth.uid() AND role = 'admin'
    ));

-- Only admins can update
CREATE POLICY "Admins can update quiz questions"
    ON public.quiz_questions FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM public.users
        WHERE id = auth.uid() AND role = 'admin'
    ));

-- Only admins can delete
CREATE POLICY "Admins can delete quiz questions"
    ON public.quiz_questions FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM public.users
        WHERE id = auth.uid() AND role = 'admin'
    ));

-- 5. RLS Policies for quiz_attempts
-- Users can read their own attempts
CREATE POLICY "Users can read own quiz attempts"
    ON public.quiz_attempts FOR SELECT
    TO authenticated USING (auth.uid() = user_id);

-- Users can insert their own attempts
CREATE POLICY "Users can insert own quiz attempts"
    ON public.quiz_attempts FOR INSERT
    TO authenticated WITH CHECK (auth.uid() = user_id);

-- Admins can read all attempts for analytics
CREATE POLICY "Admins can read all quiz attempts"
    ON public.quiz_attempts FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.users
        WHERE id = auth.uid() AND role = 'admin'
    ));

-- ============================================================
-- SEED DATA — 20+ Quiz Questions
-- NOTE: course_id is NULL here (subject-level questions).
--       After running, you can UPDATE them to link to a course:
--       UPDATE public.quiz_questions SET course_id = '<your-uuid>'
--       WHERE subject = 'Python';
-- ============================================================

INSERT INTO public.quiz_questions (subject, question, option_a, option_b, option_c, option_d, correct_answer) VALUES

-- ======== PYTHON ========
('Python',
 'What is the output of `print(type([]))`?',
 '<class ''list''>',
 '<class ''tuple''>',
 '<class ''dict''>',
 '<class ''set''>',
 'A'),

('Python',
 'Which keyword is used to define a function in Python?',
 'function',
 'def',
 'fun',
 'define',
 'B'),

('Python',
 'What does the `len()` function return?',
 'The last element of a sequence',
 'The data type of a variable',
 'The number of items in a sequence',
 'The memory address of an object',
 'C'),

('Python',
 'Which of the following is an immutable data type in Python?',
 'list',
 'dict',
 'set',
 'tuple',
 'D'),

('Python',
 'What is a lambda function in Python?',
 'A function defined using the `def` keyword with multiple lines',
 'An anonymous function defined with the `lambda` keyword',
 'A recursive function',
 'A built-in function for mathematical operations',
 'B'),

-- ======== JAVASCRIPT ========
('JavaScript',
 'Which method is used to add a new element at the end of an array in JavaScript?',
 'push()',
 'pop()',
 'shift()',
 'unshift()',
 'A'),

('JavaScript',
 'What does `===` mean in JavaScript?',
 'Assignment operator',
 'Loose equality (type coercion allowed)',
 'Strict equality (type and value must match)',
 'Not equal',
 'C'),

('JavaScript',
 'What is the output of `typeof null` in JavaScript?',
 'null',
 'undefined',
 'object',
 'string',
 'C'),

('JavaScript',
 'Which of the following is used to declare a constant in JavaScript?',
 'var',
 'let',
 'const',
 'static',
 'C'),

('JavaScript',
 'What does `JSON.stringify()` do?',
 'Parses a JSON string into a JavaScript object',
 'Converts a JavaScript object to a JSON string',
 'Formats a JSON object for display',
 'Validates a JSON string',
 'B'),

-- ======== DATA STRUCTURES ========
('Data Structures',
 'Which data structure uses LIFO (Last In First Out) order?',
 'Queue',
 'Stack',
 'Linked List',
 'Binary Tree',
 'B'),

('Data Structures',
 'What is the time complexity of searching in a Binary Search Tree (average case)?',
 'O(1)',
 'O(n)',
 'O(log n)',
 'O(n log n)',
 'C'),

('Data Structures',
 'Which data structure is best for implementing a priority queue?',
 'Array',
 'Linked List',
 'Heap',
 'Stack',
 'C'),

('Data Structures',
 'What is the worst-case time complexity of QuickSort?',
 'O(n log n)',
 'O(n)',
 'O(n²)',
 'O(log n)',
 'C'),

('Data Structures',
 'A graph with no cycles is called a?',
 'Complete Graph',
 'Multigraph',
 'Tree',
 'Directed Graph',
 'C'),

-- ======== SQL ========
('SQL',
 'Which SQL command is used to retrieve data from a database?',
 'INSERT',
 'UPDATE',
 'SELECT',
 'DELETE',
 'C'),

('SQL',
 'What does the `GROUP BY` clause do in SQL?',
 'Sorts the result set in ascending order',
 'Groups rows that have the same values into summary rows',
 'Filters rows based on a condition',
 'Joins two tables together',
 'B'),

('SQL',
 'Which SQL keyword is used to prevent duplicate values in a result set?',
 'UNIQUE',
 'DISTINCT',
 'FILTER',
 'EXCLUDE',
 'B'),

('SQL',
 'What does a PRIMARY KEY constraint ensure?',
 'Each value in the column is unique and not NULL',
 'Each value in the column can be NULL',
 'Each row references another table',
 'The column can hold duplicate values',
 'A'),

('SQL',
 'Which JOIN returns all rows from both tables, with NULLs where no match exists?',
 'INNER JOIN',
 'LEFT JOIN',
 'RIGHT JOIN',
 'FULL OUTER JOIN',
 'D'),

-- ======== WEB DEVELOPMENT ========
('Web Development',
 'What does CSS stand for?',
 'Computer Style Sheets',
 'Creative Style Sheets',
 'Cascading Style Sheets',
 'Colorful Style Sheets',
 'C'),

('Web Development',
 'Which HTML tag is used to link an external CSS stylesheet?',
 '<style>',
 '<link>',
 '<css>',
 '<script>',
 'B'),

('Web Development',
 'In REST API design, which HTTP method is used to update an existing resource?',
 'GET',
 'POST',
 'PUT',
 'DELETE',
 'C'),

('Web Development',
 'What does the `async/await` syntax enable in JavaScript?',
 'Synchronous code execution only',
 'Writing asynchronous code that looks synchronous',
 'Running code in multiple threads',
 'Compiling JavaScript to machine code',
 'B'),

('Web Development',
 'Which status code indicates a "Not Found" error in HTTP?',
 '200',
 '301',
 '403',
 '404',
 'D');

-- ============================================================
-- USEFUL ADMIN ANALYTICS QUERY (run any time in SQL editor)
-- ============================================================
/*
SELECT
    q.subject,
    q.question,
    a.selected_answer,
    a.is_correct,
    a.emotion,
    a.confidence_score,
    a.created_at
FROM public.quiz_attempts a
JOIN public.quiz_questions q ON a.question_id = q.id
ORDER BY a.created_at DESC;
*/
