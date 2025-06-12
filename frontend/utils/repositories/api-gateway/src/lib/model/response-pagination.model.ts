export interface ResponsePaginationDTO<T> {
    page?: number,
    data?: T[];
    size?: number;
}
