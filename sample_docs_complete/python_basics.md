# Python Basics for Beginners

Python is a popular, easy-to-read programming language. It is used for web development, data analysis, automation and artificial intelligence. Its simple syntax makes it a good first language for students.

## Variables and Data Types

A variable is a name that stores a value. You create one by assigning a value, for example `age = 20`. Common data types are int (whole numbers), float (decimal numbers), str (text) and bool (True or False). Python decides the type automatically, so you do not need to declare it. You can check a type with the `type()` function, for example `type(3.5)` returns float.

## Lists

A list stores an ordered collection of items inside square brackets, such as `fruits = ["apple", "mango"]`. Items are counted from index 0, so `fruits[0]` is "apple". You can add an item with `fruits.append("banana")` and find the number of items with `len(fruits)`.

## Dictionaries

A dictionary stores key-value pairs inside curly braces, such as `student = {"name": "Ali", "marks": 85}`. You read a value by using its key, for example `student["name"]` returns "Ali". You can add or change a value with `student["marks"] = 90`.

## Conditions

An if statement runs code only when a condition is true. For example, `if marks >= 50: print("Pass")` prints Pass only when marks is 50 or more. You can add an else block for the other case and an elif block for extra conditions.

## Loops

A for loop repeats code for each item in a collection, for example `for f in fruits: print(f)` prints every fruit. A while loop repeats as long as a condition stays true. Python uses indentation, not brackets, to mark which lines belong inside a block.

## Functions

A function is a reusable block of code created with the def keyword. For example, `def add(a, b): return a + b`. Calling `add(2, 3)` returns 5. Functions help avoid repeating code and make programs easier to test and read.

## Common Mistakes

Beginners often forget the colon at the end of an if, for or def line, or they mix up indentation. Another common mistake is using `=` (assignment) when `==` (comparison) is needed inside a condition.
