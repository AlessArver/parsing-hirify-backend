<ul>
<li>
  Создай виртуальное окружение <code>backend</code>
  <pre><code>python3 -m venv venv
source venv/bin/activate  # для Mac/Linux
venv\Scripts\activate     # для Windows
</code></pre>
</li>
<li>
  Установи зависимости <code>pip install -r requirements.txt</code>
</li>
<li>
  Запуск проекта <code>uvicorn main:app --reload</code>
</li>
</ul>
