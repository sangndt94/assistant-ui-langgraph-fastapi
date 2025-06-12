import { ApiRs } from "../apiRs";
import { ResponsePaginationDTO } from "../response-pagination.model";

export interface TikTokCommentRs extends ApiRs {
    data: ResponsePaginationDTO<TikTokCommentData>;
}

export interface TikTokCommentData {
    author_pin: boolean;
    aweme_id: string;
    cid: string;
    collect_stat: number;
    comment_language: string;
    comment_post_item_ids: any;
    create_time: number;
    digg_count: number;
    image_list: any;
    is_author_digged: boolean;
    is_comment_translatable: boolean;
    label_list?: LabelComment;
    label_text?: string;
    label_type?: number;
    no_show: boolean;
    reply_comment: TikTokCommentData[] | null;
    reply_comment_total?: number;
    reply_id: string;
    reply_to_reply_id: string;
    share_info: ShareInfo;
    sort_extra_score?: SortExtraScore;
    sort_tags?: string;
    status: number;
    stick_position: number;
    text: string;
    text_extra: any[];
    trans_btn_style: number;
    user: User;
    user_buried?: boolean;
    user_digged?: number;
  }
  
  export interface LabelComment {
    text: string;
    type: number;
  }
  
  export interface ShareInfo {
    acl: {
      code: number;
      extra: string;
    };
    desc: string;
    title: string;
    url: string;
  }
  
  export interface SortExtraScore {
    reply_score: number;
    show_more_score: number;
  }
  
  export interface User {
    account_labels: any;
    ad_cover_url: any;
    advance_feature_item_order: any;
    advanced_feature_info: any;
    avatar_thumb: AvatarThumb;
    bold_fields: any;
    can_message_follow_status_list: any;
    can_set_geofencing: any;
    cha_list: any;
    cover_url: any;
    custom_verify: string;
    enterprise_verify_reason: string;
    events: any;
    followers_detail: any;
    geofencing: any;
    homepage_bottom_toast: any;
    item_list: any;
    mutual_relation_avatars: any;
    need_points: any;
    nickname: string;
    platform_sync_info: any;
    predicted_age_group: string;
    relative_users: any;
    search_highlight: any;
    sec_uid: string;
    shield_edit_field_info: any;
    type_label: any;
    uid: string;
    unique_id: string;
    user_profile_guide: any;
    user_tags: any;
    white_cover_url: any;
  }
  
  export interface AvatarThumb {
    uri: string;
    url_list: string[];
    url_prefix?: string;
  }