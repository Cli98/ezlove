export const getFamilyAvatar = (person = {}) => person?.sender_avatar_url || person?.avatar_url || "";

export const getElderAvatar = (person = {}) => person?.elder_avatar_url || person?.avatar_url || "";
