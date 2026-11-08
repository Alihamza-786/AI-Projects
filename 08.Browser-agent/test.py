def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        return 'Error: Division by zero'
    return a / b

def subtract(a, b):
    return a - b

# Example usage
if __name__ == '__main__':
    num1 = 10
    num2 = 5
    print(f'Addition: {add(num1, num2)}')
    print(f'Multiplication: {multiply(num1, num2)}')
    print(f'Division: {divide(num1, num2)}')
    print(f'Subtraction: {subtract(num1, num2)}')
