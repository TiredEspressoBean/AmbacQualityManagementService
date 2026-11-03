import "axios";

declare module "axios" {
    interface AxiosRequestConfig {
        /** The caller says why the request was refused itself, so the app-wide 403
         *  interceptor (App.tsx) stays quiet instead of adding a second toast. */
        suppressErrorToast?: boolean;
    }
}
