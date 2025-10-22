import pathway as pw

t = pw.debug.table_from_markdown(
    """
    | name  | age
 1  | Alice | 15
 2  | Bob   | 32
 3  | Carole| 28
 4  | David | 35 """
)

pw.debug.compute_and_print(t)