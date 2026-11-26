/**
 * LIFE TODAY — AI NEWSROOM V1.0
 * Unified Dashboard Application Controller
 */

import { API } from "./api.js";

// Global App State
const state = {
  activeTab: "overview",
  status: null,
  articles: [],
  posts: [],
  media: [],
  sources: [],
  logs: [],
  currentModalPost: null,
  currentModalMedia: null,
};

// Notification Toast helper
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerText = message;
  toast.style.position = "fixed";
  toast.style.bottom = "24px";
  toast.style.right = "24px";
  toast.style.padding = "12px 20px";
  toast.style.borderRadius = "8px";
  toast.style.backgroundColor = type === "danger" ? "#ef4444" : (type === "success" ? "#10b981" : "#1a1f2e");
  toast.style.color = "#fff";
  toast.style.fontWeight = "600";
  toast.style.fontSize = "13px";
  toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.4)";
  toast.style.zIndex = "9999";
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// Navigation Tab Switcher
function switchTab(tabId, params = null) {
  state.activeTab = tabId;
  document.querySelectorAll(".nav-item").forEach(item => {
    item.classList.toggle("active", item.getAttribute("data-tab") === tabId);
  });
  document.querySelectorAll(".tab-pane").forEach(pane => {
    pane.classList.toggle("active", pane.id === `tab-${tabId}`);
  });

  const titles = {
    overview: "Tổng quan phòng tin Life Today",
    hunter: "Săn tin & Quét nguồn tự động",
    articles: "Kho tin mới đã thu thập",
    pending: "Bài viết chờ duyệt & Đang xử lý",
    scheduled: "Lịch đăng Facebook tự động",
    published: "Bài viết đã xuất bản",
    media: "Thư viện ảnh gốc HD & Kiểm duyệt quyền",
    sources: "Quản lý nguồn tin đa quốc gia",
    analytics: "Thống kê Content Mix & Hiệu quả",
    settings: "Cài đặt hệ thống, AI & Kết nối Meta",
    logs: "Nhật ký kiểm toán an toàn (Audit Logs)"
  };
  document.getElementById("page-title-text").innerText = titles[tabId] || "Life Today Newsroom";

  // Trigger data reload for active tab
  loadTabData(tabId, params);
}

async function loadTabData(tabId, params = null) {
  try {
    if (tabId === "overview") {
      await loadSystemStatus();
      await loadPosts();
    } else if (tabId === "hunter" || tabId === "articles") {
      await loadArticles(params || {});
    } else if (tabId === "pending" || tabId === "scheduled" || tabId === "published") {
      await loadPosts();
    } else if (tabId === "media") {
      await loadMedia();
    } else if (tabId === "sources") {
      await loadSources();
    } else if (tabId === "analytics") {
      await loadAnalytics();
    } else if (tabId === "settings") {
      await loadSettings();
    } else if (tabId === "logs") {
      await loadLogs();
    }
  } catch (err) {
    showToast(`Lỗi tải dữ liệu: ${err.message}`, "danger");
  }
}

// Data Loaders
async function loadSystemStatus() {
  const status = await API.getSystemStatus();
  state.status = status;

  document.getElementById("stat-articles").innerText = status.articles_count;
  document.getElementById("stat-pending").innerText = status.pending_posts_count;
  document.getElementById("stat-scheduled").innerText = status.scheduled_posts_count;
  document.getElementById("stat-published").innerText = status.published_posts_count;

  // Load storage stats
  try {
    const storage = await API.getStorageStats();
    const diskElem = document.getElementById("stat-storage");
    if (diskElem) {
      diskElem.innerText = `${storage.total_size_mb} MB`;
    }
  } catch (e) {}

  // Sidebar mode badge
  const modeBadge = document.getElementById("sidebar-mode-badge");
  modeBadge.innerText = status.operating_mode;
  modeBadge.className = `mode-badge badge-${status.operating_mode === 'SHADOW_MODE' ? 'warning' : 'success'}`;

  // Emergency stop toggle button
  const stopBtn = document.getElementById("btn-emergency-stop");
  if (status.emergency_stop) {
    stopBtn.innerText = "🛑 Dừng khẩn cấp: ĐANG BẬT";
    stopBtn.className = "btn btn-danger";
  } else {
    stopBtn.innerText = "🛡️ Dừng khẩn cấp: TẮT";
    stopBtn.className = "btn btn-secondary";
  }
}

async function loadArticles(params = {}) {
  const articles = await API.listArticles(params);
  state.articles = articles;
  const tbody = document.getElementById("articles-table-body");
  if (!tbody) return;

  if (articles.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:32px; color:var(--text-dim)">Chưa có tin tức nào trong danh mục này.</td></tr>`;
    return;
  }

  const flagMap = { "VN": "🇻🇳", "US": "🇺🇸", "KR": "🇰🇷", "JP": "🇯🇵", "INT": "🌏" };

  tbody.innerHTML = articles.map(a => {
    let srcLabel = a.source_name || a.source_id;
    if (!srcLabel || srcLabel === "null") {
      if (a.url) {
        try {
          srcLabel = new URL(a.url).hostname.replace('www.', '');
        } catch (e) {
          srcLabel = 'Báo chí chính thống';
        }
      } else {
        srcLabel = 'Báo chí chính thống';
      }
    }
    const countryCode = (a.country && a.country !== 'null') ? a.country.toUpperCase() : 'VN';
    const flag = flagMap[countryCode] || '🇻🇳';
    const timeDisplay = a.published_at || a.collected_at ? new Date(a.published_at || a.collected_at).toLocaleTimeString('vi-VN') : 'Mới';

    return `
    <tr>
      <td><strong>#${a.id}</strong></td>
      <td>
        <div style="font-weight:600; color:var(--text-main)">${a.title}</div>
        <div style="font-size:11px; color:var(--text-dim); margin-top:2px;">
          ${flag} <a href="${a.url || '#'}" target="_blank" style="color:var(--text-dim)">${srcLabel}</a> • ${countryCode} • ${timeDisplay}
        </div>
      </td>
      <td><span class="badge badge-info">${a.category}</span></td>
      <td><strong>${a.trend_score}</strong>/100</td>
      <td>
        <span class="badge badge-${a.post_id ? 'success' : (a.status === 'HOLD' ? 'warning' : 'gray')}">${a.post_id ? `ĐÃ CÓ BÀI #${a.post_id}` : (a.status === 'HOLD' ? 'TẠM GIỮ' : 'TIN MỚI')}</span>
        ${a.hard_block_reason ? `<div style="font-size:10px; color:#ef4444; max-width:200px;">${a.hard_block_reason}</div>` : ''}
      </td>
      <td>
        <div style="display:flex; gap:6px;">
          ${a.post_id 
            ? `<button class="btn btn-success btn-sm btn-view-post-tab" data-post-id="${a.post_id}">📝 Xem bài #${a.post_id}</button>
               <button class="btn btn-secondary btn-sm btn-process-art" data-id="${a.id}" title="Tạo lại bài viết mới cho tin này">🔄 Tạo lại</button>`
            : `<button class="btn btn-primary btn-sm btn-process-art" data-id="${a.id}">Tạo bài AI</button>
               <button class="btn btn-secondary btn-sm btn-reject-art" data-id="${a.id}">Bỏ qua</button>`
          }
        </div>
      </td>
    </tr>
  `}).join("");

  attachArticleActions();
}

function attachArticleActions() {
  document.querySelectorAll(".btn-view-post-tab").forEach(b => {
    b.onclick = () => {
      const postId = b.getAttribute("data-post-id");
      switchTab("pending");
      if (postId) {
        setTimeout(() => {
          openPostModal(parseInt(postId));
        }, 150);
      }
    };
  });

  document.querySelectorAll(".btn-process-art").forEach(b => {
    b.onclick = async () => {
      const id = b.getAttribute("data-id");
      b.disabled = true;
      b.innerText = "Đang xử lý...";
      try {
        const res = await API.processArticle(id);
        if (res.success) {
          showToast(`✅ Đã tạo bài AI thành công cho tin #${id}! Đang chuyển sang Bài chờ duyệt...`, "success");
          await loadArticles();
          await loadSystemStatus();
          await switchTab("pending");
        } else {
          showToast(`Không thể tạo bài: ${res.reason || res.error}`, "danger");
        }
      } catch (err) {
        showToast(`Lỗi: ${err.message}`, "danger");
      } finally {
        b.disabled = false;
        b.innerText = "Tạo bài AI";
      }
    };
  });

  document.querySelectorAll(".btn-reject-art").forEach(b => {
    b.onclick = async () => {
      const id = b.getAttribute("data-id");
      if (confirm(`Bạn có chắc muốn bỏ qua tin #${id}?`)) {
        await API.rejectArticle(id);
        showToast(`Đã bỏ qua tin #${id}`, "info");
        await loadArticles();
      }
    };
  });
}

async function loadPosts() {
  const posts = await API.listPosts();
  state.posts = posts;

  // Filter for tabs
  const pendingTbody = document.getElementById("pending-posts-table-body");
  const pendingTbody2 = document.getElementById("pending-posts-table-body-2");
  const scheduledTbody = document.getElementById("scheduled-posts-table-body");
  const publishedTbody = document.getElementById("published-posts-table-body");

  const pendingList = posts.filter(p => p.status === "PENDING_REVIEW" || p.status === "APPROVED" || p.status === "FAILED");
  if (pendingTbody) {
    pendingTbody.innerHTML = renderPostsTable(pendingList, "pending");
  }
  if (pendingTbody2) {
    pendingTbody2.innerHTML = renderPostsTable(pendingList, "pending");
  }

  if (scheduledTbody) {
    const scheduledList = posts.filter(p => p.status === "SCHEDULED");
    scheduledTbody.innerHTML = renderPostsTable(scheduledList, "scheduled");
  }

  if (publishedTbody) {
    const publishedList = posts.filter(p => p.status === "PUBLISHED" || p.status === "SHADOW_PUBLISHED");
    publishedTbody.innerHTML = renderPostsTable(publishedList, "published");
  }

  attachPostActions();
}

function renderPostsTable(list, type) {
  if (list.length === 0) {
    return `<tr><td colspan="6" style="text-align:center; padding:32px; color:var(--text-dim)">Không có bài viết trong mục này.</td></tr>`;
  }
  return list.map(p => {
    const mediaItem = (p.media_items && p.media_items.length > 0) ? p.media_items[0] : null;
    const thumbSrc = mediaItem ? (mediaItem.local_path ? `/media/${mediaItem.local_path.split('\\').pop().split('/').pop()}` : mediaItem.original_url) : null;

    return `
    <tr>
      <td><strong>#${p.id}</strong></td>
      <td>
        <span class="badge badge-info">${p.category}</span>
        <div style="font-size:11px; color:var(--text-dim); margin-top:4px;">${p.post_type}</div>
      </td>
      <td>
        <div style="display:flex; gap:12px; align-items:flex-start;">
          ${thumbSrc 
            ? `<img src="${thumbSrc}" style="width:60px; height:60px; border-radius:6px; object-fit:cover; flex-shrink:0; border:1px solid rgba(255,255,255,0.15);" onerror="this.style.display='none'" />` 
            : `<div style="width:60px; height:60px; border-radius:6px; background:#1e293b; display:flex; align-items:center; justify-content:center; color:var(--text-dim); font-size:10px; flex-shrink:0;">Không ảnh</div>`}
          <div style="flex:1;">
            <div style="font-size:13px; line-height:1.4; max-width:380px; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">${p.caption}</div>
            <div style="font-size:11px; color:var(--accent); margin-top:4px;">${p.hashtags || ''}</div>
          </div>
        </div>
      </td>
      <td>
        <span class="badge badge-${p.status === 'PUBLISHED' || p.status === 'SHADOW_PUBLISHED' ? 'success' : (p.status === 'SCHEDULED' ? 'info' : (p.status === 'FAILED' ? 'danger' : 'warning'))}">${p.status === 'FAILED' ? 'LỖI ĐĂNG' : p.status}</span>
        ${p.scheduled_time ? `<div style="font-size:11px; color:var(--text-dim); margin-top:4px;">Khung: ${p.target_slot || ''} (${new Date(p.scheduled_time).toLocaleString('vi-VN')})</div>` : ''}
        ${p.status === 'FAILED' && p.error_message ? `<div style="font-size:10px; color:#ef4444; max-width:220px; margin-top:4px; line-height:1.3;" title="${p.error_message.replace(/"/g, '&quot;')}">${p.error_message.slice(0, 90)}${p.error_message.length > 90 ? '...' : ''}</div>` : ''}
      </td>
      <td>
        ${p.fb_permalink ? `<a href="${p.fb_permalink}" target="_blank" style="color:var(--accent); font-size:12px; font-weight:600;">Xem bài đăng FB</a>` : '-'}
      </td>
      <td>
        <div style="display:flex; gap:6px;">
          ${type === 'pending' ? `
            <button class="btn btn-secondary btn-sm btn-edit-post" data-id="${p.id}">Chỉnh sửa</button>
            <button class="btn btn-primary btn-sm btn-publish-post" data-id="${p.id}">Đăng ngay</button>
            <button class="btn btn-secondary btn-sm btn-schedule-post" data-id="${p.id}">Lên lịch</button>
            <button class="btn btn-secondary btn-sm btn-delete-post" data-id="${p.id}" style="color:#ef4444;" title="Xóa bài viết này">🗑️ Xóa</button>
          ` : (type === 'scheduled' ? `
            <button class="btn btn-secondary btn-sm btn-edit-post" data-id="${p.id}">Chỉnh sửa</button>
            <button class="btn btn-primary btn-sm btn-publish-post" data-id="${p.id}">Đăng ngay</button>
            <button class="btn btn-secondary btn-sm btn-delete-post" data-id="${p.id}" style="color:#ef4444;" title="Xóa bài viết này">🗑️ Xóa</button>
          ` : `
            ${p.fb_permalink ? `<a href="${p.fb_permalink}" target="_blank" class="btn btn-secondary btn-sm">Xem trên FB</a>` : '<span style="color:var(--text-dim); font-size:11px;">Đã xuất bản</span>'}
            <button class="btn btn-secondary btn-sm btn-delete-post" data-id="${p.id}" style="color:#ef4444;" title="Xóa khỏi lịch sử">🗑️</button>
          `)}
        </div>
      </td>
    </tr>
  `}).join("");
}

function attachPostActions() {
  document.querySelectorAll(".btn-approve-post").forEach(b => {
    b.onclick = async () => {
      const id = b.getAttribute("data-id");
      await API.approvePost(id);
      showToast(`Đã duyệt bài viết #${id}!`, "success");
      await loadPosts();
      await loadSystemStatus();
    };
  });

  document.querySelectorAll(".btn-publish-post").forEach(b => {
    b.onclick = async () => {
      const id = b.getAttribute("data-id");
      b.disabled = true;
      b.innerText = "Đang xuất bản...";
      try {
        const res = await API.publishPostNow(id);
        if (res.success) {
          showToast(`Xuất bản thành công: ${res.message || res.fb_post_id}`, "success");
          await loadPosts();
          await loadSystemStatus();
        } else {
          showToast(`Lỗi xuất bản: ${res.error}`, "danger");
        }
      } catch (err) {
        showToast(`Lỗi: ${err.message}`, "danger");
      } finally {
        b.disabled = false;
        b.innerText = "Đăng ngay";
      }
    };
  });

  document.querySelectorAll(".btn-schedule-post").forEach(b => {
    b.onclick = async () => {
      const id = b.getAttribute("data-id");
      try {
        const res = await API.schedulePost(id);
        if (res.success) {
          showToast(`Đã xếp lịch bài #${id} vào khung ${res.slot}!`, "success");
          await loadPosts();
          await loadSystemStatus();
        }
      } catch (err) {
        showToast(`Lỗi xếp lịch: ${err.message}`, "danger");
      }
    };
  });

  document.querySelectorAll(".btn-edit-post").forEach(b => {
    b.onclick = () => {
      const id = parseInt(b.getAttribute("data-id"));
      openPostModal(id);
    };
  });

  document.querySelectorAll(".btn-delete-post").forEach(b => {
    b.onclick = async () => {
      const id = b.getAttribute("data-id");
      if (confirm(`Bạn có chắc chắn muốn xóa bài viết #${id} không?`)) {
        b.disabled = true;
        try {
          const res = await API.deletePost(id);
          if (res.success) {
            showToast(`Đã xóa bài viết #${id} thành công!`, "success");
            await loadPosts();
            await loadArticles();
            await loadSystemStatus();
          } else {
            showToast(`Lỗi xóa: ${res.error || 'Thất bại'}`, "danger");
          }
        } catch (err) {
          showToast(`Lỗi: ${err.message}`, "danger");
        } finally {
          b.disabled = false;
        }
      }
    };
  });
}

function openPostModal(id) {
  const post = state.posts.find(p => p.id === id);
  if (!post) return;
  state.currentModalPost = post;

  document.getElementById("modal-post-id").innerText = post.id;
  document.getElementById("modal-post-caption").value = post.caption;
  document.getElementById("modal-post-hashtags").value = post.hashtags || "";
  document.getElementById("modal-post-credit").value = post.credit_source || "";
  document.getElementById("modal-post-category").value = post.category;

  // Render Image Preview in Modal
  const imgElem = document.getElementById("modal-post-image-preview");
  const noImgElem = document.getElementById("modal-post-no-image");
  const urlTextElem = document.getElementById("modal-post-image-url-text");

  const mediaItem = (post.media_items && post.media_items.length > 0) ? post.media_items[0] : null;
  if (mediaItem && (mediaItem.local_path || mediaItem.original_url)) {
    const src = mediaItem.local_path ? `/media/${mediaItem.local_path.split('\\').pop().split('/').pop()}` : mediaItem.original_url;
    if (imgElem) {
      imgElem.src = src;
      imgElem.style.display = "block";
    }
    if (noImgElem) noImgElem.style.display = "none";
    if (urlTextElem) {
      urlTextElem.innerText = `Nguồn ảnh gốc: ${mediaItem.rights_source || 'Báo chí chính thống'}`;
    }
  } else {
    if (imgElem) imgElem.style.display = "none";
    if (noImgElem) noImgElem.style.display = "block";
    if (urlTextElem) urlTextElem.innerText = "";
  }

  // Handle Article Source Link
  const linkElem = document.getElementById("modal-post-source-link");
  const noLinkElem = document.getElementById("modal-post-no-link");
  const insertLinkBtn = document.getElementById("btn-modal-insert-link");
  if (post.article_url) {
    if (linkElem) {
      linkElem.href = post.article_url;
      linkElem.innerText = post.article_url;
      linkElem.style.display = "inline";
    }
    if (noLinkElem) noLinkElem.style.display = "none";
    if (insertLinkBtn) insertLinkBtn.style.display = "inline-block";
  } else {
    if (linkElem) linkElem.style.display = "none";
    if (noLinkElem) noLinkElem.style.display = "inline";
    if (insertLinkBtn) insertLinkBtn.style.display = "none";
  }

  document.getElementById("modal-post").classList.add("active");
}

async function loadMedia() {
  const media = await API.listMedia();
  state.media = media;
  const grid = document.getElementById("media-grid-container");
  if (!grid) return;

  if (media.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:48px; color:var(--text-dim)">Chưa có tệp hình ảnh nào trong thư viện.</div>`;
    return;
  }

  grid.innerHTML = media.map(m => `
    <div class="card" style="padding:14px; position:relative;">
      <div style="height:180px; background-color:#000; border-radius:var(--radius-sm); overflow:hidden; display:flex; align-items:center; justify-content:center;">
        <img src="${m.local_path ? `/media/${m.local_path.split('\\\\').pop().split('/').pop()}` : m.original_url}"
             alt="Media" style="width:100%; height:100%; object-fit:cover;"
             onerror="this.src='https://placehold.co/400x300/1a1f2e/ffffff?text=HD+Image'"/>
      </div>
      <div style="margin-top:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="badge badge-${m.quality_status === 'QUALIFIED' ? 'success' : 'warning'}">${m.quality_status}</span>
          <span class="badge badge-${m.rights_status === 'PRESS_KIT' || m.rights_status === 'VERIFIED_FREE' ? 'success' : 'danger'}">${m.rights_status}</span>
        </div>
        <div style="font-size:11px; color:var(--text-dim); margin-top:8px;">
          Kích thước: <strong>${m.width && m.height ? `${m.width}x${m.height}` : 'Ảnh gốc từ báo'}</strong> • Sắc nét: ${m.sharpness_score != null ? m.sharpness_score : 'Chưa chấm điểm'}
        </div>
        <button class="btn btn-secondary btn-sm" style="width:100%; margin-top:10px;" onclick="window.verifyMediaRights('${m.media_uuid}')">Kiểm duyệt quyền ảnh</button>
      </div>
    </div>
  `).join("");
}

window.verifyMediaRights = async (uuid) => {
  const status = prompt("Chọn quyền sử dụng cho ảnh (VERIFIED_FREE, PRESS_KIT, LICENSED, WAITING_FOR_RIGHTS, REJECTED):", "PRESS_KIT");
  if (status) {
    await API.updateMediaRights(uuid, { rights_status: status });
    showToast(`Đã cập nhật quyền ảnh thành ${status}!`, "success");
    await loadMedia();
  }
};

async function loadSources() {
  const sources = await API.listSources();
  state.sources = sources;
  const tbody = document.getElementById("sources-table-body");
  if (!tbody) return;

  tbody.innerHTML = sources.map(s => `
    <tr>
      <td><strong>${s.id}</strong></td>
      <td>
        <div style="font-weight:600">${s.name}</div>
        <a href="${s.url}" target="_blank" style="font-size:11px; color:var(--text-dim)">${s.url}</a>
      </td>
      <td>${s.country} (${s.language})</td>
      <td><span class="badge badge-info">${s.default_category}</span></td>
      <td>${s.reliability_score * 100}%</td>
      <td>
        <span class="badge badge-${s.last_status === 'HEALTHY' || s.last_status === 'ACTIVE' ? 'success' : 'warning'}">${s.last_status}</span>
      </td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="window.checkSourceHealth('${s.id}')">Kiểm tra kết nối</button>
      </td>
    </tr>
  `).join("");
}

window.checkSourceHealth = async (id) => {
  showToast(`Đang kiểm tra kết nối tới ${id}...`, "info");
  const res = await API.checkSourceHealth(id);
  showToast(`Kết quả: ${res.status}`, res.status === "HEALTHY" ? "success" : "warning");
  await loadSources();
};

async function loadAnalytics() {
  const data = await API.getContentMix();
  const container = document.getElementById("analytics-mix-container");
  if (!container) return;

  const targets = data.targets || {};
  const actual7d = data.window_7d.ratios || {};

  container.innerHTML = Object.entries(targets).map(([cat, targetRatio]) => {
    const actual = actual7d[cat] || 0.0;
    const pctTarget = (targetRatio * 100).toFixed(0);
    const pctActual = (actual * 100).toFixed(1);
    return `
      <div style="margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between; font-size:13px; font-weight:600; margin-bottom:6px;">
          <span>${cat}</span>
          <span>Thực tế: ${pctActual}% / Mục tiêu: ${pctTarget}%</span>
        </div>
        <div style="height:8px; background-color:var(--bg-secondary); border-radius:4px; overflow:hidden;">
          <div style="height:100%; width:${Math.min(actual / targetRatio * 100, 100)}%; background-color:var(--accent);"></div>
        </div>
      </div>
    `;
  }).join("");
}

async function loadSettings() {
  const status = await API.getSystemStatus();
  document.getElementById("setting-operating-mode").value = status.operating_mode;
  document.getElementById("setting-meta-page-id").value = status.meta_page_id || "";
  
  const tokenInput = document.getElementById("setting-meta-token");
  const tokenStatus = document.getElementById("meta-token-status");
  if (status.meta_configured) {
    tokenInput.value = "••••••••••••••••••••••••••••••••";
    tokenInput.placeholder = "Đã lưu Token hợp lệ (Nhập mới nếu muốn thay đổi)";
    if (tokenStatus) {
      tokenStatus.innerHTML = `<span style="color:#10b981;">✅ ĐÃ LƯU & KẾT NỐI THÀNH CÔNG: Fanpage 'Lifetoday.vn' (ID: ${status.meta_page_id})</span>`;
    }
  } else {
    tokenInput.value = "";
    tokenInput.placeholder = "Nhập Page Access Token";
    if (tokenStatus) {
      tokenStatus.innerHTML = `<span style="color:#ef4444;">⚠️ Chưa có Page Access Token. Hãy dán mã Token vào ô trên rồi bấm 'Lưu cài đặt'.</span>`;
    }
  }

  const geminiInput = document.getElementById("setting-gemini-key");
  if (status.gemini_configured) {
    geminiInput.value = "••••••••••••••••";
    geminiInput.placeholder = "Đã lưu Gemini API Key (Nhập mới nếu muốn thay đổi)";
  } else {
    geminiInput.value = "";
    geminiInput.placeholder = "Nhập Google Gemini API Key";
  }

  document.getElementById("setting-ollama-host").value = status.ollama_host || "http://localhost:11434";
}

async function loadLogs() {
  const logs = await API.getAuditLogs();
  const tbody = document.getElementById("logs-table-body");
  if (!tbody) return;

  tbody.innerHTML = logs.map(l => `
    <tr>
      <td style="white-space:nowrap; font-size:12px; color:var(--text-dim);">${new Date(l.created_at).toLocaleString('vi-VN')}</td>
      <td><span class="badge badge-info">${l.module}</span></td>
      <td><strong>${l.action}</strong></td>
      <td style="font-size:12.5px;">${l.details || '-'}</td>
    </tr>
  `).join("");
}

// Global Event Listeners & Scanner Toolbar Initialization
document.addEventListener("DOMContentLoaded", async () => {
  // Navigation
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => switchTab(item.getAttribute("data-tab")));
  });

  // Emergency Stop Toggle
  document.getElementById("btn-emergency-stop").addEventListener("click", async () => {
    const res = await API.toggleEmergencyStop();
    showToast(`Dừng khẩn cấp: ${res.emergency_stop ? 'ĐÃ KÍCH HOẠT' : 'ĐÃ TẮT'}`, res.emergency_stop ? "danger" : "success");
    await loadSystemStatus();
  });

  // Clean Storage Button (Topbar)
  document.getElementById("btn-top-clean")?.addEventListener("click", async () => {
    if (confirm("Bạn có muốn dọn dẹp các tin thô cũ quá 24h và các tệp ảnh thừa để giải phóng dung lượng ổ đĩa?")) {
      const btn = document.getElementById("btn-top-clean");
      btn.disabled = true;
      btn.innerText = "Đang dọn dẹp...";
      try {
        const res = await API.cleanupStorage(24);
        showToast(`Đã dọn dẹp thành công! Đã xóa ${res.details.purged_articles_count} tin cũ và thu gọn database.`, "success");
        await loadSystemStatus();
        await loadArticles();
      } catch (err) {
        showToast(`Lỗi dọn dẹp: ${err.message}`, "danger");
      } finally {
        btn.disabled = false;
        btn.innerText = "🧹 Dọn dẹp rác";
      }
    }
  });

  // Scan Button (Topbar)
  document.getElementById("btn-top-scan").addEventListener("click", async () => {
    const btn = document.getElementById("btn-top-scan");
    btn.disabled = true;
    btn.innerText = "Đang quét...";
    try {
      const res = await API.scanNews();
      showToast(`Đã quét ${res.sources_scanned} nguồn tin. Tìm thấy ${res.new_articles_count} tin mới!`, "success");
      await loadArticles();
      await loadSystemStatus();
    } catch (err) {
      showToast(`Lỗi quét: ${err.message}`, "danger");
    } finally {
      btn.disabled = false;
      btn.innerText = "🔍 Quét tin ngay";
    }
  });

  // Category Scanner Buttons & Time Filter Buttons
  document.querySelectorAll(".scan-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const category = btn.getAttribute("data-cat");
      const timeRange = btn.getAttribute("data-time");
      const originalText = btn.innerText;

      document.querySelectorAll(".scan-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      btn.disabled = true;

      try {
        if (category) {
          btn.innerText = "⏳ Đang quét...";
          showToast(`Đang quét tin mới: ${category}...`, "info");
          const res = await API.scanNews({ category });
          showToast(`✅ Quét ${category}: Tìm thấy ${res.new_articles_count} tin mới!`, "success");
          
          // Switch to Kho tin mới tab immediately and load filtered news
          switchTab("articles", { category });

          // Synchronize category filter buttons on articles tab
          document.querySelectorAll(".btn-filter-cat").forEach(b => {
            b.className = (b.getAttribute("data-cat") === category) ? "btn btn-sm btn-primary btn-filter-cat" : "btn btn-sm btn-secondary btn-filter-cat";
          });
        } else if (timeRange) {
          btn.innerText = "⏳ Đang lọc...";
          showToast(`⏱️ Đang lọc tin trong: ${originalText}...`, "info");
          // Switch to Kho tin mới tab immediately and filter by time range
          switchTab("articles", { time_range: timeRange });
          showToast(`✅ Đã hiển thị tin trong: ${originalText}`, "success");
        }
        await loadSystemStatus();
      } catch (err) {
        showToast(`Lỗi: ${err.message}`, "danger");
      } finally {
        btn.disabled = false;
        btn.innerText = originalText;
      }
    });
  });

  // Category Filter Buttons
  document.querySelectorAll(".btn-filter-cat").forEach(btn => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".btn-filter-cat").forEach(b => {
        b.className = "btn btn-sm btn-secondary btn-filter-cat";
      });
      btn.className = "btn btn-sm btn-primary btn-filter-cat";
      const cat = btn.getAttribute("data-cat");
      await loadArticles(cat ? { category: cat } : {});
    });
  });

  // AI Rewrite Caption inside Modal
  document.getElementById("btn-modal-ai-rewrite")?.addEventListener("click", async () => {
    if (!state.currentModalPost) return;
    const post_id = state.currentModalPost.id;
    const btn = document.getElementById("btn-modal-ai-rewrite");
    btn.disabled = true;
    btn.innerHTML = "⏳ AI đang viết...";
    try {
      const res = await API.regeneratePostCaption(post_id);
      if (res.success) {
        document.getElementById("modal-post-caption").value = res.caption;
        if (res.hashtags) document.getElementById("modal-post-hashtags").value = res.hashtags;
        showToast("✨ AI đã viết lại caption mới mượt mà!", "success");
        await loadPosts();
      } else {
        showToast("Không thể viết lại: " + (res.error || "Lỗi AI"), "danger");
      }
    } catch (err) {
      showToast("Lỗi AI: " + err.message, "danger");
    } finally {
      btn.disabled = false;
      btn.innerHTML = "✨ AI Viết lại Caption";
    }
  });

  // Insert Source Link into Caption
  document.getElementById("btn-modal-insert-link")?.addEventListener("click", () => {
    if (!state.currentModalPost || !state.currentModalPost.article_url) return;
    const captionBox = document.getElementById("modal-post-caption");
    const linkStr = `👉 Xem chi tiết tại: ${state.currentModalPost.article_url}`;
    if (!captionBox.value.includes(state.currentModalPost.article_url)) {
      captionBox.value = captionBox.value.trim() + "\n\n" + linkStr;
      showToast("Đã chèn đường link bài gốc vào cuối caption!", "success");
    } else {
      showToast("Bài viết đã có đường link này rồi!", "info");
    }
  });

  // Post Modal Save
  document.getElementById("btn-modal-save").addEventListener("click", async () => {
    if (!state.currentModalPost) return;
    const post_id = state.currentModalPost.id;
    const caption = document.getElementById("modal-post-caption").value;
    const hashtags = document.getElementById("modal-post-hashtags").value;
    const credit = document.getElementById("modal-post-credit").value;

    await API.updatePost(post_id, { caption, hashtags, credit_source: credit });
    showToast(`Đã lưu cập nhật bài viết #${post_id}!`, "success");
    document.getElementById("modal-post").classList.remove("active");
    await loadPosts();
  });

  // Post Modal Delete
  document.getElementById("btn-modal-delete")?.addEventListener("click", async () => {
    if (!state.currentModalPost) return;
    const post_id = state.currentModalPost.id;
    if (confirm(`Bạn có chắc chắn muốn xóa vĩnh viễn bài viết #${post_id} không?`)) {
      try {
        const res = await API.deletePost(post_id);
        if (res.success) {
          showToast(`Đã xóa bài viết #${post_id} thành công!`, "success");
          document.getElementById("modal-post").classList.remove("active");
          await loadPosts();
          await loadArticles();
          await loadSystemStatus();
        } else {
          showToast("Lỗi xóa: " + (res.error || "Thất bại"), "danger");
        }
      } catch (err) {
        showToast("Lỗi: " + err.message, "danger");
      }
    }
  });

  document.getElementById("btn-modal-close").addEventListener("click", () => {
    document.getElementById("modal-post").classList.remove("active");
  });

  // Settings Save
  document.getElementById("form-settings")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const mode = document.getElementById("setting-operating-mode").value;
    const metaPageId = document.getElementById("setting-meta-page-id").value;
    const metaToken = document.getElementById("setting-meta-token").value;
    const geminiKey = document.getElementById("setting-gemini-key").value;
    const ollamaHost = document.getElementById("setting-ollama-host").value;

    const payload = { operating_mode: mode };
    if (metaPageId) payload.meta_page_id = metaPageId;
    if (metaToken && !metaToken.includes("••••")) payload.meta_page_access_token = metaToken;
    if (geminiKey && !geminiKey.includes("••••")) payload.gemini_api_key = geminiKey;
    if (ollamaHost) payload.ollama_host = ollamaHost;

    await API.updateSettings(payload);
    showToast("✅ Cài đặt hệ thống đã được lưu thành công!", "success");
    await loadSystemStatus();
    await loadSettings();
  });

  // Optional Cloud PIN Gate
  const authRes = await fetch("/api/auth/status").then(r => r.json()).catch(() => ({ pin_required: false }));
  const initDashboard = async () => {
    await loadSystemStatus();
    await loadPosts();
  };

  if (authRes.pin_required) {
    const overlay = document.getElementById("pin-lock-overlay");
    const pinInput = document.getElementById("pin-lock-input");
    const pinError = document.getElementById("pin-lock-error");
    const pinBtn = document.getElementById("btn-pin-submit");
    const savedPin = localStorage.getItem("newsroom_pin") || "";

    const tryPin = async (pin) => {
      const vr = await fetch("/api/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin })
      });
      if (vr.ok) {
        localStorage.setItem("newsroom_pin", pin);
        if (overlay) overlay.style.display = "none";
        await initDashboard();
        return true;
      }
      return false;
    };

    const ok = savedPin ? await tryPin(savedPin) : false;
    if (!ok && overlay) {
      overlay.style.display = "flex";
      const submitPin = async () => {
        pinError.innerText = "";
        const val = pinInput.value.trim();
        if (!val) { pinError.innerText = "Vui lòng nhập mã PIN."; return; }
        const valid = await tryPin(val);
        if (!valid) pinError.innerText = "Mã PIN không đúng, vui lòng thử lại.";
      };
      pinBtn.onclick = submitPin;
      pinInput.onkeydown = (e) => { if (e.key === "Enter") submitPin(); };
    }
  } else {
    // Initial Data Load (Local / No PIN)
    await initDashboard();
  }
});
