#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <CoreGraphics/CoreGraphics.h>
#import <ImageIO/ImageIO.h>

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        if (argc < 2) {
            fprintf(stderr, "usage: ocr_image <image>\n");
            return 2;
        }
        NSString *path = [NSString stringWithUTF8String:argv[1]];
        NSURL *url = [NSURL fileURLWithPath:path];
        CGImageSourceRef source = CGImageSourceCreateWithURL((__bridge CFURLRef)url, NULL);
        if (!source) {
            fprintf(stderr, "failed to load image source\n");
            return 1;
        }
        CGImageRef image = CGImageSourceCreateImageAtIndex(source, 0, NULL);
        CFRelease(source);
        if (!image) {
            fprintf(stderr, "failed to load image\n");
            return 1;
        }
        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] initWithCompletionHandler:nil];
        request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
        request.usesLanguageCorrection = YES;
        request.recognitionLanguages = @[@"zh-Hans", @"en-US"];
        request.minimumTextHeight = 0.008;
        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:image options:@{}];
        NSError *error = nil;
        BOOL ok = [handler performRequests:@[request] error:&error];
        CGImageRelease(image);
        if (!ok) {
            if (error) {
                fprintf(stderr, "error domain=%s code=%ld desc=%s\n", [[error domain] UTF8String], (long)[error code], [[error localizedDescription] UTF8String]);
            } else {
                fprintf(stderr, "performRequests failed with nil error\n");
            }
            return 1;
        }
        NSArray<VNRecognizedTextObservation *> *results = request.results ?: @[];
        NSArray *sorted = [results sortedArrayUsingComparator:^NSComparisonResult(VNRecognizedTextObservation *a, VNRecognizedTextObservation *b) {
            CGFloat dy = a.boundingBox.origin.y + a.boundingBox.size.height / 2.0 - (b.boundingBox.origin.y + b.boundingBox.size.height / 2.0);
            if (fabs(dy) > 0.01) {
                return dy > 0 ? NSOrderedAscending : NSOrderedDescending;
            }
            if (a.boundingBox.origin.x < b.boundingBox.origin.x) return NSOrderedAscending;
            if (a.boundingBox.origin.x > b.boundingBox.origin.x) return NSOrderedDescending;
            return NSOrderedSame;
        }];
        fprintf(stderr, "results=%lu\n", (unsigned long)[sorted count]);
        for (VNRecognizedTextObservation *obs in sorted) {
            VNRecognizedText *txt = [[obs topCandidates:1] firstObject];
            if (txt && txt.string) {
                printf("%s\n", [txt.string UTF8String]);
            }
        }
    }
    return 0;
}
