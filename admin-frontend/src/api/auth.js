import { api } from './request'

export const login = (phone, password) =>
  api.post('/community/auth/login', { phone, password })

export const getCommunities = () =>
  api.get('/community/auth/communities')

export const switchCommunity = (communityId) =>
  api.post('/community/auth/switch-community', { community_id: communityId })
