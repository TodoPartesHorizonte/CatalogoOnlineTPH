with open('app.js', 'r', encoding='utf-8') as f:
    code = f.read()

stack = []
for idx, char in enumerate(code):
    if char == '{':
        stack.append(('{', idx))
    elif char == '}':
        if stack:
            stack.pop()
        else:
            print(f"Extra closing brace at index {idx}")
    elif char == '(':
        stack.append(('(', idx))
    elif char == ')':
        if stack:
            # find matching opening paren
            for s_idx in range(len(stack) - 1, -1, -1):
                if stack[s_idx][0] == '(':
                    stack.pop(s_idx)
                    break
        else:
            print(f"Extra closing paren at index {idx}")

if stack:
    print(f"Unmatched symbols remaining: {len(stack)}")
    for item in stack[-5:]:
        # get line number
        snippet = code[:item[1]]
        line_num = snippet.count('\n') + 1
        col_num = len(snippet) - snippet.rfind('\n')
        print(f"Unmatched '{item[0]}' on line {line_num}, col {col_num}")
else:
    print("All braces and parens matched!")
