const FAMILY_AVATARS = {
  female: [1, 2, 3].map((i) => `/static/avatars/family-female-${i}.png`),
  male: [1, 2, 3].map((i) => `/static/avatars/family-male-${i}.png`),
};

const ELDER_AVATARS = {
  female: [1, 2, 3].map((i) => `/static/avatars/elder-female-${i}.png`),
  male: [1, 2, 3].map((i) => `/static/avatars/elder-male-${i}.png`),
};

export function getPresetAvatars(role, gender) {
  if (!gender) return [];
  const avatars = role === "elder" ? ELDER_AVATARS : FAMILY_AVATARS;
  return avatars[gender] || [];
}

const FEMALE_NAMES = new Set([
  "秀英", "桂兰", "玉珍", "淑芳", "凤英", "秀珍", "翠花", "桂英", "玉兰", "美华",
  "春花", "金凤", "素芬", "丽华", "桂芳", "秀兰", "美珍", "玉芬", "凤兰", "淑华",
  "银花", "慧珍", "宝珠", "月琴", "彩云", "秀梅", "惠芳", "碧云", "巧兰", "瑞芳",
  "翠兰", "雪芬", "荷花", "素英", "慧兰", "明珠", "香莲", "云芳", "巧云", "丽珍",
]);

const MALE_NAMES = new Set([
  "建国", "国强", "志明", "永林", "德明", "文华", "正义", "明远", "天福", "长青",
  "金生", "福生", "宝林", "玉山", "大海", "光明", "家宝", "学文", "建华", "国庆",
  "振华", "锦荣", "世安", "永祥", "立功", "恒昌", "良平", "清河", "兴邦", "保国",
  "东升", "耀祖", "承恩", "润生", "树仁", "惠民", "启明", "根生", "庆丰", "定邦",
]);

function hash(value) {
  return [...String(value || "default")].reduce((sum, char) => ((sum * 31) + char.charCodeAt(0)) >>> 0, 0);
}

function identity(person, index) {
  if (typeof person === "string") return person;
  return person?.elder_user_id || person?.elder_id || person?.user_id || person?.sender_id
    || person?.elder_name || person?.elder_nickname || person?.nickname || person?.name
    || person?.id || index;
}

function genderOf(person, index) {
  const data = typeof person === "string" ? { name: person } : (person || {});
  const gender = String(data.gender ?? data.sex ?? "").toLowerCase();
  if (["female", "f", "女", "2"].includes(gender)) return "female";
  if (["male", "m", "男", "1"].includes(gender)) return "male";

  const text = [data.relation_label, data.elder_name, data.elder_nickname, data.nickname, data.name, data.sender_name]
    .filter(Boolean).join(" ");
  if (/[女妈母奶姥婆姨姑姐妹媳]/.test(text)) return "female";
  if (/[男爸父爷公叔伯哥弟婿]/.test(text)) return "male";

  const givenName = text.replace(/[（(].*$/, "").slice(-2);
  if (FEMALE_NAMES.has(givenName)) return "female";
  if (MALE_NAMES.has(givenName)) return "male";
  return hash(identity(person, index)) % 2 ? "female" : "male";
}

function pick(avatars, person, index = 0) {
  const pool = avatars[genderOf(person, index)];
  return pool[hash(identity(person, index)) % pool.length];
}

export const getFamilyAvatar = (person, index = 0) => person?.sender_avatar_url || person?.avatar_url || pick(FAMILY_AVATARS, person, index);
export const getElderAvatar = (person, index = 0) => person?.elder_avatar_url || person?.avatar_url || pick(ELDER_AVATARS, person, index);
