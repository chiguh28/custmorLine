document.addEventListener('DOMContentLoaded', function () {
    const userId = document.getElementById('user-id').value;
    let selectedCourse = null;
    let selectedDate = null;
    let selectedTime = null;
    let currentStartDate = new Date();

    // Initialize LIFF
    const liffId = document.getElementById('liff-id').value;
    if (liffId && liffId !== "None") {
        liff.init({ liffId: liffId }).catch(err => {
            console.error('LIFF Init failed', err);
        });
    }

    // Check if customer is banned FIRST, then load courses
    fetch(`/api/customer/status/${userId}`)
        .then(response => response.json())
        .then(data => {
            if (data.is_banned) {
                // Show banned message and disable booking
                document.getElementById('step1').innerHTML = `
                    <div class="alert alert-danger text-center" role="alert">
                        <h4>予約できません</h4>
                        <p>申し訳ございませんが、現在あなたは予約をご利用いただけません。</p>
                    </div>
                `;
                document.getElementById('step2').style.display = 'none';
                document.getElementById('step3').style.display = 'none';
                return; // Stop here, don't load courses
            }

            // Customer is allowed, load courses
            loadCourses();
        })
        .catch(error => {
            console.error('Error checking customer status:', error);
            // On error, still allow booking (fail-safe)
            loadCourses();
        });

    // Phone number auto-formatting
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function (e) {
            // Remove all non-digit characters
            let value = e.target.value.replace(/\D/g, '');

            // Format as XXX-XXXX-XXXX
            if (value.length > 6) {
                value = value.slice(0, 3) + '-' + value.slice(3, 7) + '-' + value.slice(7, 11);
            } else if (value.length > 3) {
                value = value.slice(0, 3) + '-' + value.slice(3);
            }

            e.target.value = value;
        });
    }

    function loadCourses() {
        // Load Courses
        fetch('/api/courses')
            .then(response => response.json())
            .then(courses => {
                const list = document.getElementById('course-list');
                courses.forEach(course => {
                    const col = document.createElement('div');
                    col.className = 'col-12 col-sm-6 col-md-4 mb-3';
                    col.innerHTML = `
                        <div class="card course-card h-100" data-id="${course.id}" data-duration="${course.duration_minutes}" data-price="${course.price}" data-name="${course.name}">
                            <div class="card-body">
                                <h5 class="card-title">${course.name}</h5>
                                <p class="card-text">${course.description}</p>
                                <p class="card-text"><strong>${course.duration_minutes}分 / ${course.price}円</strong></p>
                            </div>
                        </div>
                    `;
                    col.querySelector('.course-card').addEventListener('click', function () {
                        document.querySelectorAll('.course-card').forEach(c => c.classList.remove('selected'));
                        this.classList.add('selected');
                        selectedCourse = course;
                        document.getElementById('selected-course-id').value = course.id;
                        document.getElementById('step2').style.display = 'block';
                        loadWeekAvailability(currentStartDate);
                        document.getElementById('step2').scrollIntoView({ behavior: 'smooth' });
                    });
                    list.appendChild(col);
                });
            });
    }

    // Calendar Navigation
    document.getElementById('prev-week').addEventListener('click', function () {
        currentStartDate.setDate(currentStartDate.getDate() - 7);
        loadWeekAvailability(currentStartDate);
    });

    document.getElementById('next-week').addEventListener('click', function () {
        currentStartDate.setDate(currentStartDate.getDate() + 7);
        loadWeekAvailability(currentStartDate);
    });

    function loadWeekAvailability(startDate) {
        const startDateStr = startDate.toISOString().split('T')[0];

        // Update Label
        const endDate = new Date(startDate);
        endDate.setDate(endDate.getDate() + 6);
        document.getElementById('current-week-label').textContent =
            `${startDate.getMonth() + 1}/${startDate.getDate()} - ${endDate.getMonth() + 1}/${endDate.getDate()}`;

        fetch(`/api/availability?startDate=${startDateStr}`)
            .then(response => response.json())
            .then(data => {
                renderCalendar(startDate, data);
            });
    }

    function renderCalendar(startDate, data) {
        const headerRow = document.getElementById('calendar-header');
        const tbody = document.getElementById('calendar-body');

        // Clear existing
        // Keep first 'Time' column header
        while (headerRow.children.length > 1) {
            headerRow.removeChild(headerRow.lastChild);
        }
        tbody.innerHTML = '';

        // Generate Dates for Header
        const dates = [];
        const days = ['日', '月', '火', '水', '木', '金', '土'];
        for (let i = 0; i < 7; i++) {
            const d = new Date(startDate);
            d.setDate(d.getDate() + i);
            dates.push(d);

            const th = document.createElement('th');
            th.textContent = `${d.getMonth() + 1}/${d.getDate()}(${days[d.getDay()]})`;
            headerRow.appendChild(th);
        }

        // Generate Time Rows (10:00 - 20:00)
        const startHour = 10;
        const endHour = 20;

        for (let h = startHour; h < endHour; h++) {
            for (let m of [0, 30]) {
                const timeStr = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
                const tr = document.createElement('tr');

                // Time Column
                const tdTime = document.createElement('td');
                tdTime.textContent = timeStr;
                tr.appendChild(tdTime);

                // Date Columns
                dates.forEach(date => {
                    const dateStr = date.toISOString().split('T')[0];
                    const td = document.createElement('td');
                    const slots = data[dateStr] || [];
                    const slot = slots.find(s => s.time === timeStr);

                    if (slot && slot.status === 'available') {
                        td.textContent = '〇';
                        td.className = 'calendar-cell available';
                        td.onclick = function () {
                            // Select this slot
                            document.querySelectorAll('.calendar-cell').forEach(c => c.classList.remove('selected'));
                            this.classList.add('selected');

                            selectedDate = dateStr;
                            selectedTime = timeStr;
                            document.getElementById('selected-time').value = timeStr;

                            document.getElementById('step3').style.display = 'block';
                            updateSummary();
                            document.getElementById('step3').scrollIntoView({ behavior: 'smooth' });
                        };
                    } else {
                        td.textContent = '×';
                        td.className = 'calendar-cell disabled';
                    }
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            }
        }
    }

    function updateSummary() {
        if (selectedCourse && selectedDate && selectedTime) {
            const summary = document.getElementById('summary');
            summary.innerHTML = `
                <strong>予約内容確認</strong><br>
                コース: ${selectedCourse.name} (${selectedCourse.duration_minutes}分)<br>
                日時: ${selectedDate} ${selectedTime}<br>
                料金: ${selectedCourse.price}円
            `;
        }
    }

    // Form Submit
    document.getElementById('booking-form').addEventListener('submit', function (e) {
        e.preventDefault();

        const name = document.getElementById('name').value;
        let phone = document.getElementById('phone').value;

        // Remove hyphens
        phone = phone.replace(/-/g, '');

        if (!selectedCourse || !selectedDate || !selectedTime) {
            showResult('入力エラー', 'コースと日時を選択してください。', false);
            return;
        }

        const data = {
            userId: userId,
            courseId: selectedCourse.id,
            date: selectedDate,
            startTime: selectedTime,
            name: name,
            phone: phone
        };

        fetch('/api/reservations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
            .then(response => {
                if (response.ok) {
                    showResult('予約完了', '予約が完了しました！\nLINEに通知を送りました。', true);
                } else {
                    return response.json().then(err => {
                        showResult('予約失敗', '予約に失敗しました: ' + (err.error || '不明なエラー'), false);
                        loadWeekAvailability(currentStartDate);
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showResult('通信エラー', '通信エラーが発生しました。', false);
            });
    });

    function showResult(title, message, isSuccess) {
        document.getElementById('result-title').textContent = title;
        document.getElementById('result-message').textContent = message;
        document.getElementById('result-overlay').style.display = 'flex';

        if (isSuccess) {
            // Auto close after 3 seconds
            setTimeout(() => {
                if (liff.isInClient()) {
                    liff.closeWindow();
                }
            }, 3000);
        }
    }
});
