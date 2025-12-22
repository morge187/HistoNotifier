a, b, c, d = int(input()), int(input()), int(input()), int(input())

if (a > b and c > d or a < b or c < d):
    print(min(a, b) + 1, min(c, d) + 1)
else:
    if (max(a, b) > max(c, d)):
        print(1, max(c, d) + 1)
    else:
        print(max(a, b), 1)