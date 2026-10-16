import { BASE_URL } from "./config";
import { refreshAccessToken } from "./request";

/**
 * 通用文件上传（图片 + 视频）。
 * @param {string} tempFilePath - 本地临时文件路径
 * @param {string} [fileType] - 文件类别提示 'image' | 'video'
 * @returns {Promise<{url: string, type: string}>}
 */
export function uploadFile(tempFilePath, fileType, purpose, retried = false) {
  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync("access_token");

    // 根据文件路径后缀推断 MIME
    let mimeType = "image/jpeg";
    const lower = tempFilePath.toLowerCase();
    if (lower.endsWith(".mp4")) mimeType = "video/mp4";
    else if (lower.endsWith(".webm")) mimeType = "video/webm";
    else if (lower.endsWith(".png")) mimeType = "image/png";
    else if (lower.endsWith(".gif")) mimeType = "image/gif";
    else if (lower.endsWith(".webp")) mimeType = "image/webp";

    uni.uploadFile({
      url: `${BASE_URL}/upload${purpose ? `?purpose=${purpose}` : ""}`,
      filePath: tempFilePath,
      name: "file",
      fileType: fileType || (mimeType.startsWith("video") ? "video" : "image"),
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: async (res) => {
        let data;
        try { data = typeof res.data === "string" ? JSON.parse(res.data) : res.data; } catch (_) { data = null; }
        if (res.statusCode === 200) {
          if (data?.url) resolve(data);
          else reject(new Error("上传响应无效"));
        } else if (res.statusCode === 401 && !retried) {
          try {
            await refreshAccessToken();
            resolve(uploadFile(tempFilePath, fileType, purpose, true));
          } catch (error) {
            reject(error);
          }
        } else {
          reject(new Error(data?.detail || "上传失败"));
        }
      },
      fail: (err) => {
        reject(new Error(err?.errMsg || "上传失败"));
      },
    });
  });
}

/**
 * 兼容旧接口：上传图片，返回 URL 字符串。
 */
export function uploadImage(tempFilePath, purpose) {
  return uploadFile(tempFilePath, "image", purpose).then((r) => r.url);
}
