document.addEventListener('DOMContentLoaded', function () {
    loadDashboardData();
    loadSchedules();
    loadCourses();
    loadCustomers();

    function loadDashboardData() {
        fetch('/api/therapist/data')
            .then(response => response.json())
            .then(data => {
                // Update stats
                document.getElementById('monthly-income').textContent = `¥${data.income.toLocaleString()}`;
                document.getElementById('monthly-count').textContent = `${data.reservations.length}件`;

                // Update table
                const tbody = document.getElementById('reservation-table');
                tbody.innerHTML = '';
                data.reservations.forEach(res => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${res.reservation_date}</td>
                        <td>${res.start_time} - ${res.end_time}</td>
                        <td>${res.course_name}</td>
                        <td>${res.user_name || 'ゲスト'}</td>
                        <td>¥${res.total_price.toLocaleString()}</td>
                        <td><span class="badge bg-success">${res.status}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            })
            .catch(error => console.error('Error:', error));
    }

    function loadCourses() {
        fetch('/api/courses')
            .then(response => response.json())
            .then(courses => {
                const tbody = document.getElementById('course-table');
                tbody.innerHTML = '';
                courses.forEach(course => {
                    renderCourseRow(course);
                });
            });
    }

    function renderCourseRow(course = {}) {
        const tbody = document.getElementById('course-table');
        const tr = document.createElement('tr');
        tr.className = 'course-row';
        tr.dataset.id = course.id || '';

        tr.innerHTML = `
            <td><input type="text" class="form-control course-name" value="${course.name || ''}"></td>
            <td><input type="number" class="form-control course-duration" value="${course.duration_minutes || ''}"></td>
            <td><input type="number" class="form-control course-price" value="${course.price || ''}"></td>
            <td><input type="text" class="form-control course-desc" value="${course.description || ''}"></td>
            <td>
                <button class="btn btn-danger btn-sm" onclick="this.closest('tr').remove()">削除</button>
            </td>
        `;
        tbody.appendChild(tr);
    }

    window.addCourse = function () {
        renderCourseRow();
    };

    window.saveCourses = function () {
        const updates = [];
        document.querySelectorAll('.course-row').forEach(row => {
            const id = row.dataset.id;
            const name = row.querySelector('.course-name').value;
            const duration = row.querySelector('.course-duration').value;
            const price = row.querySelector('.course-price').value;
            const desc = row.querySelector('.course-desc').value;

            if (name && duration && price) {
                updates.push({
                    id: id ? parseInt(id) : null,
                    name: name,
                    duration: parseInt(duration),
                    price: parseInt(price),
                    description: desc
                });
            }
        });

        fetch('/api/therapist/courses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('コース情報を保存しました');
                    loadCourses(); // Reload to get new IDs
                } else {
                    alert('保存に失敗しました');
                }
            });
    };

    function loadSchedules() {
        // Load next 14 days
        const startDate = new Date();
        const endDate = new Date();
        endDate.setDate(endDate.getDate() + 13);

        const startStr = startDate.toISOString().split('T')[0];
        const endStr = endDate.toISOString().split('T')[0];

        fetch(`/api/therapist/schedules?startDate=${startStr}&endDate=${endStr}`)
            .then(response => response.json())
            .then(schedules => {
                const tbody = document.getElementById('schedule-table');
                tbody.innerHTML = '';

                const days = ['日', '月', '火', '水', '木', '金', '土'];

                for (let i = 0; i < 14; i++) {
                    const d = new Date(startDate);
                    d.setDate(d.getDate() + i);
                    const dateStr = d.toISOString().split('T')[0];
                    const dayName = days[d.getDay()];

                    // Find existing schedule
                    const sched = schedules.find(s => s.date === dateStr);
                    const startTime = sched ? sched.start_time : '10:00';
                    const endTime = sched ? sched.end_time : '20:00';
                    const isAvailable = sched ? (sched.status === 'available') : false; // Default unavailable if not set

                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${d.getMonth() + 1}/${d.getDate()}(${dayName})</td>
                        <td><input type="time" class="form-control sched-start" data-date="${dateStr}" value="${startTime}"></td>
                        <td><input type="time" class="form-control sched-end" data-date="${dateStr}" value="${endTime}"></td>
                        <td>
                            <div class="form-check form-switch">
                                <input class="form-check-input sched-status" type="checkbox" data-date="${dateStr}" ${isAvailable ? 'checked' : ''}>
                                <label class="form-check-label">${isAvailable ? '出勤' : '休み'}</label>
                            </div>
                        </td>
                    `;

                    // Add listener to update label
                    tr.querySelector('.sched-status').addEventListener('change', function () {
                        this.nextElementSibling.textContent = this.checked ? '出勤' : '休み';
                    });

                    tbody.appendChild(tr);
                }
            });
    }

    window.saveSchedules = function () {
        const updates = [];
        const rows = document.querySelectorAll('#schedule-table tr');

        rows.forEach(row => {
            const startInput = row.querySelector('.sched-start');
            const endInput = row.querySelector('.sched-end');
            const statusInput = row.querySelector('.sched-status');

            if (startInput) { // Header row check
                updates.push({
                    date: startInput.dataset.date,
                    startTime: startInput.value,
                    endTime: endInput.value,
                    status: statusInput.checked ? 'available' : 'unavailable'
                });
            }
        });

        fetch('/api/therapist/schedules', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('シフトを保存しました');
                } else {
                    alert('保存に失敗しました');
                }
            });
    };

    // --- Customer Management Functions ---

    function loadCustomers() {
        fetch('/api/therapist/customers')
            .then(response => response.json())
            .then(customers => {
                const tbody = document.getElementById('customer-table');
                tbody.innerHTML = '';

                customers.forEach(customer => {
                    const tr = document.createElement('tr');
                    tr.dataset.userId = customer.line_user_id;

                    const isBanned = customer.is_banned === 1;
                    const reservationCount = customer.reservation_count || 0;
                    const lastReservation = customer.last_reservation_date || 'なし';

                    tr.innerHTML = `
                        <td><small>${customer.line_user_id}</small></td>
                        <td class="customer-name" contenteditable="true">${customer.name || ''}</td>
                        <td class="customer-phone" contenteditable="true">${customer.phone_number || ''}</td>
                        <td>${reservationCount}件</td>
                        <td>${lastReservation}</td>
                        <td>
                            <div class="form-check form-switch">
                                <input class="form-check-input ban-toggle" type="checkbox" ${isBanned ? 'checked' : ''} onchange="toggleBan('${customer.line_user_id}', this.checked)">
                                <label class="form-check-label">${isBanned ? '出入り禁止' : '許可'}</label>
                            </div>
                        </td>
                        <td>
                            <button class="btn btn-sm btn-primary" onclick="saveCustomer('${customer.line_user_id}')">保存</button>
                            <button class="btn btn-sm btn-danger" onclick="deleteCustomer('${customer.line_user_id}')">削除</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            })
            .catch(error => console.error('Error loading customers:', error));
    }

    window.saveCustomer = function (userId) {
        const row = document.querySelector(`tr[data-user-id="${userId}"]`);
        const name = row.querySelector('.customer-name').textContent;
        const phone = row.querySelector('.customer-phone').textContent;
        const isBanned = row.querySelector('.ban-toggle').checked;

        fetch(`/api/therapist/customers/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                phone_number: phone,
                is_banned: isBanned
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('顧客情報を保存しました');
                } else {
                    alert('保存に失敗しました');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('保存中にエラーが発生しました');
            });
    };

    window.deleteCustomer = function (userId) {
        if (!confirm('この顧客を削除しますか?関連する予約も削除されます。')) {
            return;
        }

        fetch(`/api/therapist/customers/${userId}`, {
            method: 'DELETE'
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('顧客を削除しました');
                    loadCustomers(); // Reload the list
                } else {
                    alert('削除に失敗しました');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('削除中にエラーが発生しました');
            });
    };

    window.toggleBan = function (userId, isBanned) {
        const row = document.querySelector(`tr[data-user-id="${userId}"]`);
        const label = row.querySelector('.ban-toggle').nextElementSibling;
        label.textContent = isBanned ? '出入り禁止' : '許可';

        // Auto-save when toggling ban status
        const name = row.querySelector('.customer-name').textContent;
        const phone = row.querySelector('.customer-phone').textContent;

        fetch(`/api/therapist/customers/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                phone_number: phone,
                is_banned: isBanned
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log('Ban status updated');
                } else {
                    alert('更新に失敗しました');
                    // Revert the toggle
                    row.querySelector('.ban-toggle').checked = !isBanned;
                    label.textContent = !isBanned ? '出入り禁止' : '許可';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('更新中にエラーが発生しました');
            });
    };
});
